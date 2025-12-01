from translatepy import Translator

t = Translator()
print(t.translate(text="lucky winners will be awarded 600,000 Birr every day for 100 days." , source_language="en", destination_language="am"))  # 100k+ chars works, no key, no limit