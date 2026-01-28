import time
import random
import os
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
import json

load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def analyze_image_mock(image_path_or_url, simulation_override=None):
    """
    Hybrid function: 
    1. Checks for Simulation Override (User Forces Result).
    2. Tries Gemini API (if key exists and no override).
    3. Falls back to Mock (Random/Filename).
    """
    
    # 0. Simulation Override
    if simulation_override and simulation_override != "auto":
        time.sleep(1.0)
        if simulation_override == "damp":
            return {
                "defect_type": "moisture",
                "val_defect_name": "damped wall",
                "severity": "critical",
                "confidence": 0.99,
                "description": "Simulated: Detected severe dampness and potential mold.",
                "action": "Urgent: Waterproofing required immediately."
            }
        elif simulation_override == "wiring":
             return {
                "defect_type": "electrical",
                "val_defect_name": "exposed wiring",
                "severity": "critical",
                "confidence": 0.99,
                "description": "Simulated: Exposed electrical wiring detected.",
                "action": "Danger: Isolate circuit and call electrician."
            }
        elif simulation_override == "structural":
             return {
                "defect_type": "structural",
                "val_defect_name": "structural cracks",
                "severity": "high",
                "confidence": 0.99,
                "description": "Simulated: Major structural cracking detected.",
                "action": "Consult structural engineer."
            }
        elif simulation_override == "ok":
             return {
                "defect_type": "none",
                "val_defect_name": "ok",
                "severity": "ok",
                "confidence": 0.99,
                "description": "Simulated: No defects found.",
                "action": "None"
            }
    
    # 1. Try Gemini API
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel('gemini-pro-vision')
            
            # Load Image
            if isinstance(image_path_or_url, str):
                sim_path = image_path_or_url
                # If using local file storage pattern from s3.py, it might be an absolute path
                if os.path.exists(sim_path):
                     img = Image.open(sim_path)
                else:
                     return _mock_fallback(image_path_or_url)
            else:
                return _mock_fallback(image_path_or_url)

            prompt = """
            Analyze this image of a room/property for defects. 
            Return a JSON object ONLY with the following keys:
            - defect_type: One of ["moisture", "electrical", "structural", "finishing", "none"]
            - val_defect_name: Short name (e.g. "damp", "crack", "wire", "ok")
            - severity: One of ["critical", "high", "medium", "low", "ok"]
            - confidence: Float (0.0-1.0)
            - description: Brief description not exceeding 20 words.
            - action: Recommended action not exceeding 10 words.
            
            Focus on detecting: Water/Damp, Exposed Wiring, Cracks.
            """
            
            response = model.generate_content([prompt, img])
            text = response.text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)
            
            return {
                "defect_type": result.get("defect_type", "none").lower(),
                "val_defect_name": result.get("val_defect_name", "ok"),
                "severity": result.get("severity", "ok").lower(),
                "confidence": result.get("confidence", 0.9),
                "description": result.get("description", "Analyzed by AI"),
                "action": result.get("action", "None")
            }
            
        except Exception as e:
            print(f"Gemini API Error: {e}")
            # Fall through to mock
    
    return _mock_fallback(image_path_or_url)

def _mock_fallback(image_path_or_url):
    """Fallback Mock logic based on keywords or random weights."""
    time.sleep(1.0)
    filename = str(image_path_or_url).lower()
    
    # Keyword detection
    if any(x in filename for x in ["damp", "wet", "mold", "water"]):
        return {"defect_type": "moisture", "val_defect_name": "damped wall", "severity": "critical", "confidence": 0.96, "description": "Detected dampness.", "action": "Treat mold."}
    if any(x in filename for x in ["wire", "cable", "electric"]):
         return {"defect_type": "electrical", "val_defect_name": "exposed wiring", "severity": "critical", "confidence": 0.98, "description": "Exposed wiring.", "action": "Call electrician."}
    if any(x in filename for x in ["crack", "split"]):
        return {"defect_type": "structural", "val_defect_name": "cracks", "severity": "high", "confidence": 0.92, "description": "Structural cracks.", "action": "Engineer check."}

    # Random Fallback
    outcomes = [
        {"type": "moisture", "name": "damped wall", "sev": "critical", "desc": "Wall saturation detected.", "act": "Waterproof now."},
        {"type": "electrical", "name": "exposed wiring", "sev": "critical", "desc": "Dangerous wiring detected.", "act": "Fix wiring."},
        {"type": "structural", "name": "structural cracks", "sev": "high", "desc": "Wall fractures detected.", "act": "Monitor cracks."},
        {"type": "none", "name": "ok", "sev": "ok", "desc": "No defects.", "act": "None."}
    ]
    # Default to finding something for demo
    choice = random.choices(outcomes, weights=[30, 30, 30, 10], k=1)[0]
    return {
        "defect_type": choice["type"], "val_defect_name": choice["name"], 
        "severity": choice["sev"], "confidence": 0.9, 
        "description": choice["desc"], "action": choice["act"]
    }

def analyze_document_text(text_content):
    """
    Analyzes text from an inspection report to extract summary and suggestions.
    Uses Gemini Pro if available, otherwise mocks.
    """
    
    # 1. Try Gemini API
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel('gemini-pro')
            
            prompt = f"""
            You are an expert civil engineer. Read the following technical inspection report text and provide:
            1. A concise summary (max 3 sentences).
            2. A list of actionable suggestions/changes based on defects (max 3 items).
            
            Input Text:
            "{text_content[:2000]}..." 
            
            Return output as JSON with keys: "ai_summary", "ai_suggestions".
            """
            
            response = model.generate_content(prompt)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
            
        except Exception as e:
            print(f"Gemini Text API Error: {e}")
            # Fallback
            
    # Mock Fallback
    time.sleep(1.5)
    return {
        "ai_summary": "Simulated Analysis: The document appears to clearly outline structural and moisture issues. It recommends immediate waterproofing.",
        "ai_suggestions": "- Apply hydrophobic coating to exterior walls.\n- Replace corroded piping in the utility area.\n- verify load-bearing columns."
    }

def compare_findings_with_report(ai_findings_text, inspector_report_text):
    """
    Compares AI visual findings vs Inspector's textual report.
    Returns similarity score and differences.
    """
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"""
            Compare these two sets of findings from a property inspection:
            
            Set A (AI Visual Analysis):
            {ai_findings_text[:2000]}
            
            Set B (Inspector's Report):
            {inspector_report_text[:2000]}
            
            Task:
            1. Calculate a "Similarity Score" (0-100) representing how much Set A agrees with Set B.
            2. List "Matches" (Issues found in BOTH).
            3. List "Discrepancies" (Issues found in ONE but NOT the other).
            
            Return JSON:
            {{
                "similarity_score": int,
                "matches": ["item1", "item2"],
                "discrepancies": ["item1", "item2"],
                "summary": "Brief analysis of comparison"
            }}
            """
            response = model.generate_content(prompt)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            print(f"Comparison Error: {e}")
            
    # Mock
    time.sleep(1.5)
    return {
        "similarity_score": 85,
        "matches": ["Damp in Master Bedroom verified", "Kitchen wiring issues verified"],
        "discrepancies": ["AI detected hairline cracks in Living Room (Not in Report)", "Inspector notes roof tile damage (AI did not see roof)"],
        "summary": "High agreement on major interior issues. AI found minor wall cracks missed by report. Report includes exterior roof analysis not covered by AI images."
    }
