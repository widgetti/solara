<template>
    <main class="pcm-demo">
        <header class="pcm-hero">
            <span class="pcm-eyebrow">Solara transport demo</span>
            <h1>Streaming audio</h1>
            <p>Hear a synth melody while Python is still sending it. The audio is generated on demand by your Solara kernel.</p>
        </header>

        <section class="pcm-player" aria-label="Audio player">
            <div class="pcm-player-heading">
                <div>
                    <h2>Synth melody</h2>
                    <p>{{ sample_rate / 1000 }} kHz mono · 16-bit PCM · {{ duration }} seconds of audio</p>
                </div>
                <div class="pcm-controls">
                    <button class="pcm-play" type="button" :disabled="active" @click="play">Play</button>
                    <button class="pcm-stop" type="button" :disabled="!active" @click="stop">Stop</button>
                </div>
            </div>
            <div class="pcm-wave" :class="{ 'pcm-wave-live': active && firstByteMs !== null }" aria-hidden="true">
                <span v-for="(height, index) in wave" :key="index" :style="{ height: height + '%', animationDelay: index * -35 + 'ms' }"></span>
            </div>
            <p class="pcm-status" role="status">{{ status }}</p>
            <dl class="pcm-metrics">
                <div><dt>First bytes</dt><dd>{{ firstByteMs === null ? "–" : firstByteMs + " ms" }}</dd></div>
                <div><dt>Download complete</dt><dd>{{ completeMs === null ? "–" : completeMs + " ms" }}</dd></div>
                <div><dt>Audio received</dt><dd>{{ (receivedBytes / 1024).toFixed(1) }} KiB</dd></div>
            </dl>
        </section>

        <section class="pcm-explainer" aria-labelledby="pcm-how">
            <h2 id="pcm-how">From Python to your speakers</h2>
            <ol>
                <li><strong>Register.</strong> Play asks the kernel for a fresh, single-use URL. Registration only stores the generator factory.</li>
                <li><strong>Generate.</strong> The browser’s GET starts the factory. It waits two seconds to mimic a TTS service, then generates an ascending and descending melody in 100 ms chunks of signed, little-endian PCM.</li>
                <li><strong>Play.</strong> The browser reads the response body and queues samples in Web Audio as they arrive. Stop aborts the request and closes the audio context.</li>
            </ol>
            <p>The two timers start at the browser’s GET. Compare them to see how much earlier playback can begin. The excerpts focus on the streaming loop. The app source includes synthesis, PCM decoding, and audio scheduling.</p>
            <div class="pcm-code-grid">
                <details open>
                    <summary>Python · generate and register</summary>
                    <pre><code v-text="pythonSnippet"></code></pre>
                </details>
                <details open>
                    <summary>Browser · read bytes as they arrive</summary>
                    <pre><code v-text="browserSnippet"></code></pre>
                </details>
            </div>
        </section>
    </main>
</template>

<style id="pcm-streaming-demo">
.pcm-demo {
    width: 100%;
    max-width: 64rem;
    min-width: 0;
    box-sizing: border-box;
    margin: 0 auto;
    padding: clamp(1rem, 4vw, 3rem);
    color: #15243c;
    font-family: system-ui, sans-serif;
}
.pcm-demo .pcm-hero {
    padding: clamp(1.5rem, 5vw, 3rem);
    border-radius: 1.5rem;
    background: linear-gradient(115deg, #102641, #185e65);
    color: #fff;
}
.pcm-demo .pcm-eyebrow {
    color: #9be8db;
    font-size: .75rem;
    font-weight: 750;
    letter-spacing: .13em;
    text-transform: uppercase;
}
.pcm-demo h1 {
    margin: .35rem 0 .5rem;
    font-size: clamp(2.25rem, 6vw, 4rem);
    line-height: 1.05;
}
.pcm-demo h2 { margin: 0 0 .25rem; font-size: 1.35rem; }
.pcm-demo p { margin: 0; }
.pcm-demo .pcm-hero p { max-width: 33rem; color: #e1f3f3; }
.pcm-demo .pcm-player, .pcm-demo .pcm-explainer {
    margin-top: 1rem;
    padding: clamp(1rem, 3vw, 1.75rem);
    border: 1px solid #d9e5ec;
    border-radius: 1.25rem;
    background: #f8fbfd;
}
.pcm-demo .pcm-player-heading, .pcm-demo .pcm-controls {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: .65rem;
}
.pcm-demo .pcm-player-heading { justify-content: space-between; }
.pcm-demo .pcm-player-heading p, .pcm-demo dt { color: #485c73; }
.pcm-demo button {
    min-width: 5.25rem;
    min-height: 2.75rem;
    padding: .5rem 1rem;
    border: 1px solid #137368;
    border-radius: .75rem;
    font-weight: 700;
    cursor: pointer;
}
.pcm-demo .pcm-play { background: #126b61; color: #fff; }
.pcm-demo .pcm-stop { background: #fff; color: #12574e; }
.pcm-demo button:hover:not(:disabled) { box-shadow: 0 0 0 2px #65cbbd; }
.pcm-demo button:disabled { opacity: .48; cursor: default; }
.pcm-demo .pcm-wave {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: clamp(2px, .65vw, 7px);
    height: 4.75rem;
    margin: 1.15rem 0 .75rem;
    border-radius: .8rem;
    background: #e4f3f1;
}
.pcm-demo .pcm-wave span {
    width: clamp(3px, 1.1vw, 9px);
    border-radius: 6px;
    background: #20857a;
    opacity: .55;
}
.pcm-demo .pcm-wave-live span { opacity: 1; animation: pcm-pulse .65s ease-in-out infinite alternate; }
@keyframes pcm-pulse { from { transform: scaleY(.42); } to { transform: scaleY(1); } }
@media (prefers-reduced-motion: reduce) { .pcm-demo .pcm-wave-live span { animation: none; } }
.pcm-demo .pcm-status { min-height: 1.5em; color: #12574e; font-weight: 650; }
.pcm-demo .pcm-metrics, .pcm-demo .pcm-code-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
    gap: .75rem;
    margin: .85rem 0 0;
}
.pcm-demo .pcm-metrics div {
    padding: .7rem .85rem;
    border: 1px solid #d9e5ec;
    border-radius: .75rem;
    background: #fff;
}
.pcm-demo dt { font-size: .85rem; }
.pcm-demo dd { margin: .15rem 0 0; font-size: 1.25rem; font-weight: 750; font-variant-numeric: tabular-nums; }
.pcm-demo ol { padding-left: 1.5rem; margin: .5rem 0 .85rem; }
.pcm-demo li + li { margin-top: .4rem; }
.pcm-demo details { min-width: 0; border-radius: .75rem; background: #102641; color: #e7f5f6; }
.pcm-demo summary { padding: .75rem 1rem; cursor: pointer; font-weight: 700; }
.pcm-demo pre { margin: 0; padding: 0 1rem 1rem; overflow: auto; font-size: .82rem; line-height: 1.6; }
.pcm-demo pre code { color: inherit; background: transparent; padding: 0; box-shadow: none; }
</style>

<script>
export default {
    data: () => ({
        requestId: 0,
        active: false,
        status: "Ready to stream",
        firstByteMs: null,
        completeMs: null,
        receivedBytes: 0,
        wave: [15, 28, 54, 76, 50, 28, 21, 40, 68, 88, 62, 33, 19, 33, 62, 88, 68, 40, 21, 28, 50, 76, 54, 28, 15],
        pythonSnippet: `from solara.server.streaming import register_stream

async def synth_phrase():
    await asyncio.sleep(2)
    for note_index, note in enumerate(MELODY):
        frequency = 440 * 2 ** ((note - 69) / 12)
        for chunk in range(CHUNKS_PER_NOTE):
            yield pcm_chunk(frequency, chunk)
            if note_index < len(MELODY) - 1 or chunk < CHUNKS_PER_NOTE - 1:
                await asyncio.sleep(0.1)

url = register_stream(synth_phrase)`,
        browserSnippet: `const abort = new AbortController();
const response = await fetch(url, {
    signal: abort.signal,
    credentials: "same-origin"
});
const reader = response.body.getReader();

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    queuePcmForPlayback(value);
}`
    }),
    watch: {
        ticket(ticket) {
            if (this.active && ticket.id === this.requestId) {
                if (ticket.error) {
                    this.stop();
                    this.status = ticket.error;
                } else {
                    this.stream(ticket.url, this.playback);
                }
            }
        }
    },
    beforeDestroy() {
        this.stop();
    },
    beforeUnmount() {
        this.stop();
    },
    methods: {
        async play() {
            this.firstByteMs = null;
            this.completeMs = null;
            this.receivedBytes = 0;
            this.active = true;
            this.status = "Preparing stream…";
            const id = ++this.requestId;
            try {
                const audio = new AudioContext();
                this.playback = { audio, abort: new AbortController() };
                await audio.resume();
                if (this.active && id === this.requestId) {
                    this.prepare(id);
                }
            } catch (error) {
                if (id === this.requestId) {
                    this.stop();
                    this.status = error.message;
                }
            }
        },
        stop() {
            if (this.playback) {
                this.playback.abort.abort();
                this.playback.audio.close();
                this.playback = null;
                this.status = "Stopped";
            }
            this.active = false;
        },
        async stream(url, playback) {
            const { audio, abort } = playback;
            const requested = performance.now();
            let nextTime = 0;
            let trailing = new Uint8Array(0);
            const wait = () => new Promise(resolve => setTimeout(resolve, 25));
            this.status = "Waiting for audio from Python…";
            try {
                const response = await fetch(url, { signal: abort.signal, credentials: "same-origin" });
                if (!response.ok) {
                    throw new Error(`Stream returned HTTP ${response.status}`);
                }
                const reader = response.body.getReader();
                while (!abort.signal.aborted) {
                    const { done, value } = await reader.read();
                    if (done) {
                        break;
                    }
                    if (abort.signal.aborted) {
                        return;
                    }
                    this.receivedBytes += value.length;
                    if (this.firstByteMs === null) {
                        this.firstByteMs = Math.round(performance.now() - requested);
                        this.status = `First bytes in ${this.firstByteMs} ms. Playing…`;
                    }
                    const bytes = new Uint8Array(trailing.length + value.length);
                    bytes.set(trailing);
                    bytes.set(value, trailing.length);
                    const view = new DataView(bytes.buffer);
                    const count = Math.floor(bytes.length / 2);
                    trailing = bytes.slice(count * 2);
                    for (let offset = 0; offset < count; offset += 2400) {
                        while (nextTime - audio.currentTime > 0.35 && !abort.signal.aborted) {
                            await wait();
                        }
                        if (abort.signal.aborted) {
                            return;
                        }
                        const size = Math.min(2400, count - offset);
                        const buffer = audio.createBuffer(1, size, this.sample_rate);
                        const samples = buffer.getChannelData(0);
                        for (let i = 0; i < size; i++) {
                            samples[i] = view.getInt16((offset + i) * 2, true) / 32768;
                        }
                        const source = audio.createBufferSource();
                        source.buffer = buffer;
                        source.connect(audio.destination);
                        nextTime = Math.max(nextTime, audio.currentTime + 0.02);
                        source.start(nextTime);
                        nextTime += buffer.duration;
                    }
                }
                if (!abort.signal.aborted) {
                    this.completeMs = Math.round(performance.now() - requested);
                    this.status = `Download complete in ${this.completeMs} ms.`;
                    while (nextTime > audio.currentTime && !abort.signal.aborted) {
                        await wait();
                    }
                }
            } catch (error) {
                if (!abort.signal.aborted) {
                    this.status = error.message;
                }
            } finally {
                if (this.playback === playback) {
                    abort.abort();
                    audio.close();
                    this.playback = null;
                    this.active = false;
                }
            }
        }
    }
}
</script>
