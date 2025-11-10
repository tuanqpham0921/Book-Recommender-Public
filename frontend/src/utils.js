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
        yield parsed;
      }
    } catch (err) {
      console.error("Failed to parse SSE data:", value.data, err);
      yield { type: "raw", text: value.data };
    }
  }
}