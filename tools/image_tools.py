import logging
import os
from typing import Any, Callable, Iterable, Optional

logger = logging.getLogger(__name__)

try:  # pragma: no cover - exercised indirectly via integration tests
    import crewai_tools as ct
except Exception:  # pragma: no cover - optional dependency guard
    ct = None
    logger.warning("crew_ai_tools_unavailable")
if ct is not None:
    BaseTool = ct.BaseTool
    CREW_TOOLS_AVAILABLE = True
else:

    class BaseTool:  # type: ignore[override] - minimal stub
        name: str = "crew_ai_stub_base_tool"
        description: str = "Stub for crewai tools when dependency is unavailable."

        def __call__(self, *args, **kwargs):
            return self._run(*args, **kwargs)

        async def _arun(self, *args, **kwargs):  # pragma: no cover - sync flows dominate
            return self._run(*args, **kwargs)

        def _run(self, *args, **kwargs):  # pragma: no cover - to be overridden
            raise NotImplementedError

    CREW_TOOLS_AVAILABLE = False

from leonardo_ai_sdk import LeonardoAiSDK

SDK = LeonardoAiSDK(api_key=os.environ.get("LEONARDO_API_KEY", ""))


class LeonardoImageTool(BaseTool):
    name: str = "Leonardo Image Generation Tool"
    description: str = "Генерирует изображение по текстовому промпту. Используй это для создания маркетинговых материалов."
    _cached_client: Optional[LeonardoAiSDK] = None

    def _get_client(self) -> Optional[LeonardoAiSDK]:
        api_key = os.environ.get("LEONARDO_API_KEY", "")
        if not api_key:
            return None

        if self._cached_client and getattr(self._cached_client, "api_key", None) == api_key:
            return self._cached_client

        if getattr(SDK, "api_key", None) == api_key:
            self._cached_client = SDK
            return self._cached_client

        self._cached_client = LeonardoAiSDK(api_key=api_key)
        return self._cached_client

    def _call_generation(self, client: LeonardoAiSDK, prompt: str) -> Any:
        payload = {
            "prompt": prompt,
            "model_id": "1e663234-9A62-4E31-8F46-8203E70366E4",
            "num_images": 1,
            "width": 1024,
            "height": 1024,
        }

        call_paths: Iterable[tuple[Iterable[str], str]] = (
            (("image",), "create_generation"),
            (("image",), "generate_image"),
            (("generations",), "create_generation"),
            (("generations",), "create"),
            (tuple(), "post_generations"),
        )

        last_error: Optional[Exception] = None
        for attr_chain, method_name in call_paths:
            target: Any = client
            try:
                for attr in attr_chain:
                    target = getattr(target, attr)
                method: Callable[..., Any] = getattr(target, method_name)
            except AttributeError as error:
                last_error = error
                continue

            try:
                return method(**payload)
            except TypeError as error:
                last_error = error
                continue

        if last_error:
            raise RuntimeError("Leonardo SDK generation API is unavailable") from last_error
        raise RuntimeError("Leonardo SDK generation API could not be resolved")

    def _extract_image_url(self, response: Any) -> Optional[str]:
        if response is None:
            return None

        data: Any = response
        for accessor in ("model_dump", "dict"):
            if hasattr(response, accessor):
                try:
                    data = getattr(response, accessor)()
                    break
                except Exception:  # pragma: no cover - best effort
                    continue
        else:
            if hasattr(response, "__dict__") and not isinstance(response, dict):
                data = response.__dict__

        if isinstance(data, dict):
            paths = (
                ("generations", 0, "generated_images", 0, "url"),
                ("image_generations", 0, "image_url"),
                ("images", 0, "url"),
                ("data", "image_url"),
                ("imageUrl",),
                ("url",),
            )
            for path in paths:
                current: Any = data
                try:
                    for key in path:
                        if isinstance(current, dict):
                            current = current[key]
                        else:
                            current = current[key]
                    if isinstance(current, str):
                        return current
                except (KeyError, IndexError, TypeError):
                    continue

        # Some SDK responses expose attributes instead of dicts.
        for attribute in ("generations", "image_generations", "images"):
            if hasattr(response, attribute):
                try:
                    collection = getattr(response, attribute)
                    if collection:
                        candidate = getattr(collection[0], "generated_images", None)
                        if candidate:
                            first = candidate[0]
                            url = getattr(first, "url", None)
                            if isinstance(url, str):
                                return url
                        url = getattr(collection[0], "url", None)
                        if isinstance(url, str):
                            return url
                except Exception:  # pragma: no cover - best effort
                    continue

        return None

    def _run(self, prompt: str) -> dict:
        client = self._get_client()
        if not client or not getattr(client, "api_key", None):
            return {
                "status": "error",
                "message": "LEONARDO_API_KEY отсутствует. Генерация изображения пропущена.",
            }

        try:
            response = self._call_generation(client, prompt)
            image_url = self._extract_image_url(response)
            if not image_url:
                raise ValueError("Leonardo SDK не вернул ссылку на изображение.")
            return {"status": "success", "image_url": image_url}
        except Exception as error:
            return {"status": "error", "message": str(error)}


print("Модуль tools/image_tools.py инициализирован.")
