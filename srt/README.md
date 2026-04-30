


Testing stream using ffmpeg:

```bash
ffplay -fflags nobuffer -flags low_delay "srt://127.0.0.1:8888?mode=listener&latency=50"
```

This starts the listening server and shows the stream in a window. You can adjust the latency as needed.