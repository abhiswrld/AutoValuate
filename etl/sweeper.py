import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

async def check_url(session, url, semaphore):
    async with semaphore:
        # Wait 2 seconds before each request
        await asyncio.sleep(2)
        try:
            async with session.get(url, headers=HEADERS, timeout=10) as response:
                if response.status in [404, 410]:
                    return url, 'dead'
                elif response.status == 403:
                    return url, 'banned'
                else:
                    return url, 'alive'
        except Exception as e:
            return url, 'error'

async def sweep_chunk(urls):
    semaphore = asyncio.Semaphore(2) # Max 2 concurrent requests
    async with aiohttp.ClientSession() as session:
        tasks = [check_url(session, url, semaphore) for url in urls]
        return await asyncio.gather(*tasks)

def run_sweeper():
    print("--- Running Dead Link Sweeper ---")
    with engine.begin() as conn:
        # 1. Automated 30-Day TTL Wipe
        print("1. Executing 30-Day TTL Wipe...")
        result = conn.execute(text("DELETE FROM cars WHERE created_at < NOW() - INTERVAL '30 days'"))
        print(f"Deleted {result.rowcount} expired 30-day listings.\n")
        
        # 2. Async Sweep (grab 500 oldest cars that haven't been checked recently)
        # We can add a 'last_checked' column to prevent re-checking the same ones over and over
        conn.execute(text('ALTER TABLE cars ADD COLUMN IF NOT EXISTS last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP'))
        
        query = text("""
            SELECT url FROM cars 
            ORDER BY last_checked ASC, created_at ASC
            LIMIT 500
        """)
        cars_to_check = [row[0] for row in conn.execute(query).fetchall()]
    
    if not cars_to_check:
        print("No cars to check.")
        return

    print(f"2. Async sweeping {len(cars_to_check)} URLs...")
    results = asyncio.run(sweep_chunk(cars_to_check))
    
    dead_urls = []
    banned = False
    
    for url, status in results:
        if status == 'dead':
            dead_urls.append(url)
        elif status == 'banned':
            banned = True
            break
            
    if banned:
        print("CRITICAL: Received 403 Forbidden. Craigslist is blocking these requests. IP ban likely if continued. Stopping async sweep.")
        return

    with engine.begin() as conn:
        # Update last_checked for all URLs we just checked
        if cars_to_check:
            # Doing a quick bulk update of last_checked
            conn.execute(text("UPDATE cars SET last_checked = CURRENT_TIMESTAMP WHERE url = ANY(:urls)"), {"urls": cars_to_check})
            
        # Delete dead URLs
        if dead_urls:
            conn.execute(text("DELETE FROM cars WHERE url = ANY(:urls)"), {"urls": dead_urls})
            print(f"Sweeper deleted {len(dead_urls)} dead/sold cars from the market.")
        else:
            print("No dead cars found in this chunk.")

if __name__ == "__main__":
    run_sweeper()
