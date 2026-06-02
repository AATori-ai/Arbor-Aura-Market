from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import time
import json

router = APIRouter()

class AIAnalyzeRequest(BaseModel):
    filename: str

@router.post("/analyze-image")
async def analyze_image(req: AIAnalyzeRequest):
    api_key = os.getenv("GEMINI_API_KEY")
    
    if api_key:
        try:
            from google import genai
            from google.genai import types
            
            # The image should be in the uploads folder
            img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", req.filename)
            
            if not os.path.exists(img_path):
                raise HTTPException(status_code=404, detail="Image not found for AI analysis")
                
            client = genai.Client(api_key=api_key)
            
            # Use gemini-2.5-flash for fast multimodal reasoning
            prompt = """
            You are an expert second-hand market appraiser for a Finnish marketplace.
            Analyze this image and return a JSON object with the following fields:
            - "title": A catchy, concise title for the item in Finnish.
            - "description": A short, appealing description (2-3 sentences) in Finnish.
            - "price": A fair estimated second-hand market price in Euros (just the number).
            - "category": Choose the best matching category from this list: [Elektroniikka, Ajoneuvot, Koti, Muoti, Urheilu, Lapset, Kirjat, Palvelut, Lemmikit].
            
            Only return the raw JSON object, no markdown blocks.
            """
            
            # Read image
            from PIL import Image
            img = Image.open(img_path)
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[img, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            
            data = json.loads(response.text)
            return data
            
        except Exception as e:
            print(f"AI Gen Error: {str(e)}")
            # Fall through to mock if Gemini fails for some reason
            pass

    # MOCK FALLBACK (If no API key or if API failed)
    time.sleep(1.5) # Simulate processing time
    return {
        "title": "Tyylikäs löytö (AI-Arvio)",
        "description": "Erittäin hyväkuntoinen tuote, joka etsii uutta kotia. Täydellinen arjen käyttöön tai keräilyyn. Vastaa uudenveroista.",
        "price": 45,
        "category": "Koti"
    }
