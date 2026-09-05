"""OpenRouter chat completions API utils."""

import asyncio
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI, APIConnectionError, APITimeoutError, RateLimitError
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from tqdm.asyncio import tqdm_asyncio

load_dotenv()


def get_openrouter_client() -> AsyncOpenAI:
    """Get an AsyncOpenAI client configured for OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in .env file!")

    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def get_openai_client() -> AsyncOpenAI:
    """Get an AsyncOpenAI client configured for OpenAI."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file!")

    return AsyncOpenAI(api_key=api_key)


@retry(
    retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
async def call_api(
    client: AsyncOpenAI,
    model: str,
    messages: list,
    response_format: type[BaseModel] | None = None,
    temperature: float = 1.0,
    max_tokens: int = 16000,
    top_p: float = 1.0,
    logprobs: bool = False,
    top_logprobs: int | None = None,
    n: int = 1,
    stop: list[str] | str | None = None,
    tools: list[dict] | None = None,
    extra_body: dict | None = None,
    **kwargs,
):
    """
    Make a chat completion API call.

    Args:
        client: AsyncOpenAI client.
        model: Model identifier.
        messages: Chat messages.
        response_format: Pydantic model for structured output.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens in response.
        top_p: Nucleus sampling threshold.
        logprobs: Enable logprobs.
        top_logprobs: Number of top logprobs to return.
        n: Number of completions to generate.
        stop: Stop sequence(s) to end generation.
        tools: Tool definitions for function calling.
        extra_body: Extra parameters to pass in request body (e.g., top_k for OpenRouter).
        **kwargs: Additional parameters forwarded to the API call (e.g., parallel_tool_calls, seed).

    Returns:
        Full response object from the API.
    """
    if response_format is not None:
        response = await client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            logprobs=logprobs,
            top_logprobs=top_logprobs,
            response_format=response_format,
            extra_body=extra_body,
            **kwargs,
        )
    else:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            logprobs=logprobs,
            top_logprobs=top_logprobs,
            n=n,
            stop=stop,
            tools=tools,
            extra_body=extra_body,
            **kwargs,
        )
    return response


async def process_one(
    client: AsyncOpenAI,
    model: str,
    messages: list,
    semaphore: asyncio.Semaphore,
    response_format: type[BaseModel] | None = None,
    temperature: float = 1.0,
    max_tokens: int = 16000,
    top_p: float = 1.0,
    logprobs: bool = False,
    top_logprobs: int | None = None,
    extra_body: dict | None = None,
    **kwargs,
):
    """Process a single request with semaphore-based concurrency control."""
    async with semaphore:
        try:
            return await call_api(
                client=client,
                model=model,
                messages=messages,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                logprobs=logprobs,
                top_logprobs=top_logprobs,
                extra_body=extra_body,
                **kwargs,
            )
        except Exception as e:
            if "ValidationError" in type(e).__name__ or "json" in str(e).lower():
                print(f"  WARNING: Structured output parse failed: {e!r:.200}")
                return None
            raise


async def process_batch(
    client: AsyncOpenAI,
    model: str,
    messages_list: list,
    response_format: type[BaseModel] | None = None,
    temperature: float = 1.0,
    max_tokens: int = 16000,
    max_concurrent: int = 10,
    top_p: float = 1.0,
    logprobs: bool = False,
    top_logprobs: int | None = None,
    extra_body: dict | None = None,
    return_exceptions: bool = False,
    **kwargs,
) -> list:
    """
    Process all requests concurrently with a semaphore.

    Args:
        client: AsyncOpenAI client.
        model: Model identifier.
        messages_list: List of chat message lists.
        response_format: Pydantic model for structured output.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens in response.
        max_concurrent: Maximum concurrent requests.
        top_p: Nucleus sampling threshold.
        logprobs: Enable logprobs.
        top_logprobs: Number of top logprobs to return.
        extra_body: Extra parameters to pass in request body (e.g., top_k for OpenRouter).
        return_exceptions: If True, exceptions are returned in results instead of raised.
        **kwargs: Additional parameters forwarded to the API call (e.g., parallel_tool_calls, seed).

    Returns:
        List of response objects from the API.
        If return_exceptions=True, failed requests return Exception objects.
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    coroutines = [
        process_one(
            client=client,
            model=model,
            messages=m,
            semaphore=semaphore,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            logprobs=logprobs,
            top_logprobs=top_logprobs,
            extra_body=extra_body,
            **kwargs,
        )
        for m in messages_list
    ]

    if return_exceptions:
        # tqdm_asyncio.gather doesn't support return_exceptions, use asyncio.gather
        # with tqdm wrapper for progress tracking
        async def wrap_with_progress(coro, pbar):
            try:
                result = await coro
                pbar.update(1)
                return result
            except Exception as e:
                pbar.update(1)
                return e

        from tqdm import tqdm
        pbar = tqdm(total=len(coroutines))
        wrapped = [wrap_with_progress(c, pbar) for c in coroutines]
        results = await asyncio.gather(*wrapped)
        pbar.close()
        return results
    else:
        return await tqdm_asyncio.gather(*coroutines)
