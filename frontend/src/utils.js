import { EventSourceParserStream } from 'eventsource-parser/stream';

export async function* parseSSEStream(stream) {
  const sseReader = stream
    .pipeThrough(new TextDecoderStream())
    .pipeThrough(new EventSourceParserStream())
    .getReader();

  while (true) {
    const { done, value } = await sseReader.read();
    if (done) break;

    try {
      if (value?.data) {
        const parsed = JSON.parse(value.data);
        yield parsed; // now it's an object/dict
      }
    } catch (err) {
      console.error("❌ Failed to parse SSE data:", value.data, err);
      // optionally still yield the raw string if parse fails
      yield { type: "raw", text: value.data };
    }
  }
}