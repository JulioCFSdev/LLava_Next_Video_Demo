from fastapi import FastAPI, UploadFile, File, Form
from transformers import LlavaNextVideoForConditionalGeneration, LlavaNextVideoProcessor
import numpy as np
import av
from io import BytesIO
import json

app = FastAPI()

# Carregar o processador e o modelo
processor = LlavaNextVideoProcessor.from_pretrained("llava-hf/LLaVA-NeXT-Video-7B-hf")
model = LlavaNextVideoForConditionalGeneration.from_pretrained("llava-hf/LLaVA-NeXT-Video-7B-hf", device_map={"": "cpu"})

# Função para ler vídeo usando PyAV
def read_video_pyav(container, indices):
    frames = []
    container.seek(0)
    for i, frame in enumerate(container.decode(video=0)):
        if i in indices:
            frames.append(frame.to_ndarray(format="rgb24"))
    return np.stack(frames)

# Função para processar o arquivo de vídeo
def process_video(file: UploadFile):
    video_bytes = file.file.read()
    container = av.open(BytesIO(video_bytes))
    total_frames = container.streams.video[0].frames
    indices = np.linspace(0, total_frames - 1, num=8, dtype=int)  # Amostra 8 frames do vídeo
    return read_video_pyav(container, indices)

@app.post("/process_video/")
async def process_video_endpoint(
    question: str = Form(...),  # Recebe a pergunta como uma string
    video: UploadFile = File(...),  # Recebe o vídeo
):
    """
    Recebe um vídeo e uma pergunta (como uma string), processa o vídeo e gera uma resposta com o modelo LLaVa-NeXT-Video.
    """
    print(question)
    print(video)
    # Criar a estrutura do conversation automaticamente
    conversation = {
        "role": "user",
        "content": [
            {"type": "text", "text": question},  # Aqui é onde a pergunta será inserida
            {"type": "video"}  # Representa o conteúdo do vídeo
        ]
    }

    # Processar o vídeo
    video_frames = process_video(video)
    
    # Criar o prompt usando o template de conversa
    prompt = processor.apply_chat_template([conversation], add_generation_prompt=True)

    # Processar as entradas (vídeos e prompts)
    inputs = processor([prompt], videos=[video_frames], padding=True, return_tensors="pt").to(model.device)

    # Parâmetros de geração
    generate_kwargs = {"max_new_tokens": 100, "do_sample": True, "top_p": 0.9}

    # Gerar a resposta
    output = model.generate(**inputs, **generate_kwargs)

    # Decodificar a resposta gerada
    generated_text = processor.batch_decode(output, skip_special_tokens=True)

    return {"generated_text": generated_text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="192.168.0.54", port=8000)  # Usando o IP local

