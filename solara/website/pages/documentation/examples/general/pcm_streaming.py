"""Stream generated audio from a Solara kernel to the browser.

Run this example with `solara run solara/website/pages/documentation/examples/general/pcm_streaming.py`
and click **Play**. The browser requests a fresh URL and plays the first PCM chunk while
the remaining chunks are generated. The player displays the time to the first bytes
and the time to completion. **Stop** aborts the fetch and stops playback.

The same factory can stream bytes from a TTS API. Open the upstream connection inside
the async generator so it opens on GET and closes when the browser cancels. This API
supports Starlette and FastAPI. Route the stream GET and the kernel websocket to the
same worker, and configure any reverse proxy to pass chunks through as they arrive.
"""

import asyncio
import math
import struct
from typing import AsyncGenerator, Callable, Dict, Union

import solara
from solara.server.streaming import register_stream

SAMPLE_RATE = 24_000
CHUNK_SAMPLES = 2_400


MELODY = (60, 64, 67, 72, 71, 67, 64, 62, 65, 69, 72, 77, 76, 72, 67, 60)
CHUNKS_PER_NOTE = 5


def pcm_chunk(frequency: float, chunk: int) -> bytes:
    note_samples = CHUNKS_PER_NOTE * CHUNK_SAMPLES
    start = chunk * CHUNK_SAMPLES
    samples = []
    for index in range(start, start + CHUNK_SAMPLES):
        phase = 2 * math.pi * frequency * index / SAMPLE_RATE
        envelope = min(1, index / 480, (note_samples - 1 - index) / 1440)
        samples.append(int(envelope * (6500 * math.sin(phase) + 1700 * math.sin(2 * phase))))
    return struct.pack(f"<{CHUNK_SAMPLES}h", *samples)


async def synth_phrase() -> AsyncGenerator[bytes, None]:
    await asyncio.sleep(2)
    for note_index, note in enumerate(MELODY):
        frequency = 440 * 2 ** ((note - 69) / 12)
        for chunk in range(CHUNKS_PER_NOTE):
            yield pcm_chunk(frequency, chunk)
            if note_index < len(MELODY) - 1 or chunk < CHUNKS_PER_NOTE - 1:
                await asyncio.sleep(0.1)


@solara.component_vue("pcm_player.vue")
def PcmPlayer(ticket: Dict[str, Union[int, str]], event_prepare: Callable[[int], None], sample_rate: int, duration: float):
    pass


@solara.component
def Page():
    initial_ticket: Dict[str, Union[int, str]] = {}
    ticket, set_ticket = solara.use_state(initial_ticket)

    def prepare(request_id: int):
        try:
            url = register_stream(synth_phrase)
        except RuntimeError as error:
            set_ticket({"id": request_id, "error": str(error)})
        else:
            set_ticket({"id": request_id, "url": url})

    PcmPlayer(ticket=ticket, event_prepare=prepare, sample_rate=SAMPLE_RATE, duration=len(MELODY) * CHUNKS_PER_NOTE * CHUNK_SAMPLES / SAMPLE_RATE)
