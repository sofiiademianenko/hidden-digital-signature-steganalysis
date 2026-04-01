# Hidden Digital Signature using Steganography and Neural Steganalysis

![Python](https://img.shields.io/badge/Python-3.9-blue)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-orange)
![Status](https://img.shields.io/badge/Status-Research-green)

---

## Overview

This project implements a method of hidden electronic signature embedding using LSB steganography and evaluates its robustness using a CNN-based steganalysis model.

The approach combines ECDSA digital signatures with steganographic embedding to ensure both authenticity and concealment of digital documents.

---

## Objectives

- Develop a method for hidden electronic signature generation  
- Embed signatures into images using LSB steganography  
- Build a CNN-based steganalysis model  
- Evaluate robustness against neural steganalysis  

---

## Technologies Used

- Python 3.9  
- TensorFlow / Keras  
- NumPy  
- OpenCV / PIL  
- Matplotlib  

---

## Methodology

### 1. Signature Generation
- Electronic signature generated using ECDSA  
- Converted into a binary sequence  

### 2. Steganographic Embedding
- Signature embedded using LSB method  
- All RGB channels are used  

### 3. Dataset Preparation
- Based on BOSSbase dataset  
- Balanced classes: `cover` and `stego`  
- Split: train / validation / test  

### 4. Steganalysis Model
- CNN with High-Pass Filter (HPF)  
- Designed to detect subtle embedding artifacts  

---

## Experimental Results

### Base Case (512-bit signature)
- Accuracy: **50%**  
- Detection: - Not detected  
- PSNR: **76.28 dB**  

### Increased Payload (*8)
- Accuracy: **100%**  
- Detection: + Fully detected  
- PSNR: **67.47 dB**  

**Conclusion:** Detection strongly depends on payload size  

---

## Visualization

### Base Case (512-bit payload)
![Training](images/training_50.png)
![Confusion Matrix](images/confusion_50.png)

### Increased Payload (*8)
![Training](images/training_100.png)
![Confusion Matrix](images/confusion_100.png)

---

## Project Structure

```bash
hidden_ep/
│
├── dataset/              # Main dataset (512-bit payload)
├── dataset_exp/          # Extended dataset (×8 payload)
├── boss_base/            # Original images
├── prepared_cover/       # Preprocessed images
│
├── keys/                 # ECDSA keys
├── output/               # Base experiment results
├── output_exp/           # Extended experiment results
├── test_data/            # Sample files
│
├── dataset_generator.py
├── train.py
├── evaluate.py
├── steganalysis_model.py
│
├── lsb_steganography.py
├── signer.py
├── verifier.py
├── key_manager.py
│
├── cli.py
├── gui.py
├── utils.py
│
└── README.md
```
28 directories, 54047 files
---

## How to Run
```bash
python dataset_generator.py
python train.py
python evaluate.py
```

---

## Notes
Large datasets and generated outputs are not included in the repository
The project was developed for research and educational purposes

## Author
Sofiia Demianenko
