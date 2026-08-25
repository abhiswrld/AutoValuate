import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_SENDER = "autovaluate.alerts@gmail.com" # Default placeholder, user would use their own

engine = create_engine(DATABASE_URL)

def send_alert_email(to_email, car_details, alert_criteria):
    if not GMAIL_APP_PASSWORD:
        print("Missing GMAIL_APP_PASSWORD, skipping email.")
        return
        
    msg = MIMEMultipart()
    msg['From'] = GMAIL_SENDER
    msg['To'] = to_email
    msg['Subject'] = f"AutoValuate Alert: {car_details['year']} {car_details['make'].title()} {car_details['model'].title()} Found!"
    
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #4F46E5;">AutoValuate Alert Match!</h2>
        <p>We found a new car that matches your alert criteria ({alert_criteria}):</p>
        
        <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; margin-top: 15px;">
            <h3>{car_details['year']} {car_details['make'].title()} {car_details['model'].title()}</h3>
            <p><strong>Price:</strong> ${car_details['price']}</p>
            <p><strong>AI Value:</strong> ${car_details['predicted_price']} (You save ${car_details['predicted_price'] - car_details['price']})</p>
            <p><strong>Location:</strong> {car_details['location'].title()}</p>
            <p><strong>Mileage:</strong> {car_details['mileage']} miles</p>
            <a href="{car_details['url']}" style="display: inline-block; background-color: #4F46E5; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 10px;">View Listing</a>
        </div>
      </body>
    </html>
    """
    
    msg.attach(MIMEText(html, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Alert sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

def process_alerts():
    print("Processing active alerts...")
    
    with engine.connect() as conn:
        alerts = conn.execute(text("""
            SELECT u.id, u.user_id, u.make, u.model, u.max_price, u.region, p.email
            FROM user_alerts u
            JOIN profiles p ON u.user_id = p.id
        """)).fetchall()
        
        for alert in alerts:
            alert_id, user_id, make, model, max_price, region, email = alert
            
            # Find cars added in the last 24 hours that match
            query = """
                SELECT year, make, model, price, predicted_price, location, mileage, url
                FROM cars
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                AND predicted_price > price
            """
            params = {}
            
            if make:
                query += " AND make = :make"
                params['make'] = make
            if model:
                query += " AND model = :model"
                params['model'] = model
            if max_price:
                query += " AND price <= :max_price"
                params['max_price'] = max_price
            if region:
                query += " AND (region = :region OR location ILIKE :loc_like)"
                params['region'] = region
                params['loc_like'] = f"%{region}%"
                
            query += " ORDER BY difference DESC LIMIT 1"
            
            match = conn.execute(text(query), params).fetchone()
            if match:
                car_details = {
                    "year": match[0], "make": match[1], "model": match[2],
                    "price": match[3], "predicted_price": match[4],
                    "location": match[5], "mileage": match[6], "url": match[7]
                }
                
                # In a real app we'd mark this alert as "triggered" so we don't spam them
                criteria = f"{make.title()} {model.title()} under ${max_price} in {region.title()}"
                send_alert_email(email, car_details, criteria)
                
                # Delete the alert so it only fires once (one-shot alert)
                with engine.begin() as wconn:
                    wconn.execute(text("DELETE FROM user_alerts WHERE id = :id"), {"id": alert_id})

if __name__ == "__main__":
    process_alerts()
