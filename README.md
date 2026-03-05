# 🎬 Movie Recommender System

A content-based recommendation system that suggests similar movies using  
**TF-IDF vectorization and cosine similarity**, built with **FastAPI** and **Streamlit**.

#Teckstack Used
![Python](https://img.shields.io/badge/Python-3.10-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-red)
![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)


## System Architecture

```text
User
  │
  ▼
Streamlit Frontend
  │
  ▼
FastAPI Backend
  │
  ▼
Recommendation Engine
(TF-IDF + Cosine Similarity)
  │
  ▼
Preprocessed Movie Dataset (.pkl files)
```
