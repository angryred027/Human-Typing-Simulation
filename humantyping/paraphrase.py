"""Lazy wrapper around a local T5 paraphrase model (e.g. humarin/
chatgpt_paraphraser_on_T5_base). The model files are loaded from a user path at
runtime — never bundled — so heavy torch/transformers deps stay optional."""


class Paraphraser:
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self._tok = None
        self._model = None

    def _ensure(self) -> None:
        if self._model is None:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            self._tok = AutoTokenizer.from_pretrained(self.model_path)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(self.model_path)

    def paraphrase(self, text: str) -> str | None:
        try:
            self._ensure()
            import torch
            ids = self._tok(f"paraphrase: {text}", return_tensors="pt",
                            truncation=True, max_length=128).input_ids
            with torch.no_grad():
                out = self._model.generate(ids, max_length=128, do_sample=True,
                                           top_p=0.95, temperature=0.9, num_return_sequences=1)
            return self._tok.decode(out[0], skip_special_tokens=True).strip()
        except Exception:
            return None
