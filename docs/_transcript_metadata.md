
```python
transcript.metadata["sample_id"]        # sample uuid 
transcript.metadata["id"]               # dataset sample id 
transcript.metadata["epoch"]            # sample epoch
transcript.metadata["sample_metadata"]  # sample metadata
transcript.metadata["score"]            # main sample score 
transcript.metadata["score_<scorer>"]   # named sample scores
```

See the `LogMetadata` class for details on all of the fields included in `transcript.metadata`.
