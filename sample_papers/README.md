# Sample Papers

Place sample research papers (PDF files) in this directory for testing.

## Recommended test papers

1. **ML Benchmarks**: Any paper from arXiv that reports model performance on standard benchmarks
2. **Drug Trials**: Any clinical trial paper from PubMed Central (open access)
3. **Material Properties**: Any materials science paper with property tables

## How to get test papers

```bash
# Example: Download the "Attention Is All You Need" paper
# (or any open-access paper from arXiv)
```

Test the extraction pipeline:
```bash
python run_demo.py --pdf sample_papers/your_paper.pdf --schema ml_benchmarks
```
