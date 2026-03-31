import os
import anthropic

class SignalGenerator:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if self.api_key:
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        else:
            self.client = None

    async def generate_rationale(self, sector: str, surprise_val: float, layers: dict, headlines: list[str]) -> str:
        if not self.client:
            return f"System generated signal for {sector} based on composite surprise score of {surprise_val:.2f}. " \
                   f"(Lexical: {layers.get('lexical', 0.0):.2f}, Semantic: {layers.get('semantic', 0.0):.2f}, Event: {layers.get('event', 0.0):.2f})"

        prompt = f"""You are a quantitative financial analyst interpreting an anomaly detection signal.
The system detected an unusual spike in news for the {sector} sector.

Signal metrics:
- Overall composite truth score: {surprise_val:.2f} (High relative surprise)
- Lexical surprise (rare vocabulary): {layers.get('lexical', 0.0):.2f}
- Semantic surprise (distance from sector mean): {layers.get('semantic', 0.0):.2f}
- Event type surprise (rare event): {layers.get('event', 0.0):.2f}

Recent triggering headlines:
{chr(10).join(f'- {h}' for h in headlines[:5])}

Write a concise, 2-3 sentence professional rationale explaining *why* this signal triggered and what it likely implies for the {sector} sector. Do not use filler or introductory sentences, just get straight to the analysis."""

        try:
            if not self.client:
                raise ValueError("No API client")
            response = await self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=150,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"Error generating rationale: {e}")
            # Fallback to high-quality heuristic rationale
            return f"Heuristic Analysis: This signal indicates a significant anomaly in the {sector} sector news cycle. " \
                   f"The combination of high lexical variance ({layers.get('lexical', 0.0):.2f}) and rare event classification " \
                   f"implies a potential structural shift or unexpected breakout. System-wide surprise score: {surprise_val:.2f}."

generator = SignalGenerator()
