import os
from crewai_tools import BaseTool
from leonardo_ai import Leonardo


class LeonardoImageTool(BaseTool):
    name: str = "Leonardo Image Generation Tool"
    description: str = "Генерирует изображение по текстовому промпту. Используй это для создания маркетинговых материалов."
    _leo: Leonardo = None

    def _get_client(self) -> Leonardo:
        if self._leo:
            return self._leo
        api_key = os.environ.get("LEONARDO_API_KEY")
        if not api_key:
            raise ValueError("LEONARDO_API_KEY должен быть установлен.")
        self._leo = Leonardo(auth_token=api_key)
        return self._leo

    def _run(self, prompt: str) -> dict:
        try:
            client = self._get_client()
            response = client.post_generations(
                prompt=prompt,
                model_id="1e663234-9A62-4E31-8F46-8203E70366E4",  # Leonardo Phoenix
                num_images=1,
                width=1024,
                height=1024
            )
            image_url = response.generations[0].generated_images[0].url
            return {"status": "success", "image_url": image_url}
        except Exception as e:
            return {"status": "error", "message": str(e)}


print("Модуль tools/image_tools.py инициализирован.")
