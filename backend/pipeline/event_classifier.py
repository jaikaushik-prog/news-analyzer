import os
import anthropic
import json

class EventClassifier:
    def __init__(self):
        # We will initialize this cleanly later or inject the api key
        # For simplicity in this module, we'll try to read from env or pass it
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if self.api_key:
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        else:
            self.client = None
            print("Warning: ANTHROPIC_API_KEY not found. Falling back to keyword classification.")
            
        self.event_types = [
            "Earnings Report", "M&A", "Regulatory", "Management Change", 
            "Product Launch", "Macroeconomic", "Legal/Lawsuit", "Analyst Rating", "Other"
        ]

    def _fallback_classify(self, text: str) -> str:
        t = text.lower()
        if "earn" in t or "q1" in t or "q2" in t or "q3" in t or "q4" in t or "revenue" in t:
            return "Earnings Report"
        if "acquir" in t or "merg" in t or "buyout" in t or "takeover" in t:
            return "M&A"
        if "sec" in t or "fcc" in t or "regulat" in t or "probe" in t or "investigat" in t:
            return "Regulatory"
        if "ceo" in t or "cfo" in t or "resign" in t or "step down" in t or "appoint" in t:
            return "Management Change"
        if "launch" in t or "unveil" in t or "release" in t:
            return "Product Launch"
        if "fed" in t or "rate" in t or "inflation" in t or "job" in t or "cpi" in t:
            return "Macroeconomic"
        if "lawsuit" in t or "sue" in t or "court" in t or "settle" in t:
            return "Legal/Lawsuit"
        if "upgrade" in t or "downgrade" in t or "target" in t:
            return "Analyst Rating"
        return "Other"

    async def classify(self, text: str) -> str:
        # Exact match cache to skip API
        if not self.client:
            return self._fallback_classify(text)
            
        # This is the single-item interface, but internally we can use it
        # or prefer the batch interface if we have many at once.
        results = await self.classify_batch([text])
        return results[0] if results else "Other"

    async def classify_batch(self, texts: list[str]) -> list[str]:
        if not self.client or not texts:
            return [self._fallback_classify(t) for t in texts]

        # Filter out duplicates and cache hits
        # (For this batch implementaton, we'll just process the batch as is but 
        # ensure we follow the structured format)
        
        prompt = f"""Classify the following financial news headlines into EXACTLY ONE of these categories:
{', '.join(self.event_types)}

Return a JSON array of objects, where each object has "index" (0-based) and "category" keys.

Headlines:
"""
        for i, t in enumerate(texts):
            prompt += f"{i}. \"{t}\"\n"

        prompt += "\nFormat: [{\"index\": 0, \"category\": \"...\"}, ...]"

        try:
            response = await self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=600,
                temperature=0.0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            raw_content = response.content[0].text.strip()
            # Try to find JSON array in response
            import re
            json_match = re.search(r'\[.*\]', raw_content, re.DOTALL)
            if json_match:
                results_json = json.loads(json_match.group(0))
                # Map back to original order
                mapped = ["Other"] * len(texts)
                for item in results_json:
                    idx = item.get("index")
                    cat = item.get("category")
                    if idx is not None and idx < len(texts) and cat in self.event_types:
                        mapped[idx] = cat
                return mapped
            return [self._fallback_classify(t) for t in texts]
        except Exception as e:
            print(f"Error classifying batch with Anthropic: {e}")
            return [self._fallback_classify(t) for t in texts]

classifier = EventClassifier()
