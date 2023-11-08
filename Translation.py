from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


# translates from "language" to English
class Translator:
    def __init__(self, language):
        if language == "DE":
            self.tokenizer = AutoTokenizer.from_pretrained("google/bert2bert_L-24_wmt_de_en", pad_token="<pad>",
                                                           eos_token="</s>", bos_token="<s>")
            self.model = AutoModelForSeq2SeqLM.from_pretrained("google/bert2bert_L-24_wmt_de_en")
        else:
            print(f"ERROR: {language} is not supported")

    def translate(self, text):
        input_ids = self.tokenizer(text, return_tensors="pt", add_special_tokens=False).input_ids
        output_ids = self.model.generate(input_ids)[0]
        return self.tokenizer.decode(output_ids, skip_special_tokens=True)
