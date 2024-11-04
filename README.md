# Im2Toy
### Turn any object to their's cute character toy counterpart

![image](https://github.com/user-attachments/assets/b86a0bea-499e-488b-a765-95a9b01f510a)

![image](https://github.com/user-attachments/assets/de5a7938-5455-4d2d-b9bd-1d3de2db8efe)

## Overview
The **Im2Toy Pipeline** is a computer vision and natural language processing (NLP) project designed to transform real-world images into toy-like representations. This pipeline leverages object detection, segmentation, and text-to-image generation to convert items into stylized, toy versions with a plastic, shiny appearance on a simple background.

## Table of Contents
1. [Workflow](#workflow)
2. [Features](#features)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [Usage](#usage)
6. [Future Improvements](#future-improvements)

---

## Workflow
The pipeline follows these steps to process an input image into a toy-like version:

1. **Keyword Extraction**  
   - Use **Gemini Flash** to capture key keywords from the image, identifying the main subject and context.

2. **Object Detection**  
   - Run **YOLOWorld** to detect objects and generate bounding boxes based on keywords extracted from the first stage.
   - Filter bounding boxes by:
     - **Confidence**: Minimum confidence score threshold.
     - **Position and Size**: Prioritize objects closer to the center and based on relative area within the image.

3. **Object Segmentation**  
   - Select the bounding box with the highest score.
   - Apply **SAMv2 (Segment Anything Model)** to create a segment mask, isolating the main object from the background.

4. **Detailed Description Generation**  
   - Use **Gemini Flash** to further describe the extracted object.
   - Modify keywords for toy-like characteristics, adding descriptions like "plastic," "shiny," and "white background."

5. **Image-to-Toy Conversion**  
   - Feed the refined prompt into a **text-to-image model** to generate a toy-like representation of the object.

## Features
- **Automatic Keyword Extraction**: Identifies the main subject in images for targeted object detection.
- **Efficient Object Detection and Segmentation**: Uses YOLOWorld and SAMv2 to isolate objects of interest accurately.
- **Detailed Prompt Refinement**: Enhances object descriptions to create toy-like characteristics.
- **Image-to-Toy Transformation**: Converts isolated objects into toy representations with a text-to-image model.

## Requirements
- **Python 3.8+**
- **Libraries**:
  - YOLOWorld for object detection with open vocab
  - SAMv2 for segmentation
  - Gemini Flash for keyword extraction, image description generation and toy description modification.
  - Text-to-image model (e.g., DALL-E, Stable Diffusion) for toy conversion

## Installation
Clone this repository and navigate to the project directory:
```bash
git clone https://github.com/vTuanpham/Im2Toy.git
cd Im2Toy
```

Install dependencies with:
```bash
bash setup.sh
```

Set `GOOGLE_API_KEY`:
Get yours here: https://aistudio.google.com/apikey
```bash
export GOOGLE_API_KEY=<YOUR_GOOGLE_API_KEY>
```
It's free!

## Usage
1. **Run the FastAPI server**:
   ```bash
   python main.py
   ```

2. **Access via [localhost](http://127.0.0.1:8001)**:
   ![image](https://github.com/user-attachments/assets/8e5b6db1-d945-4168-9131-542b32771a1b)


## Future Improvements
- **Additional Style Options**: Add options for generating toys in different styles (e.g., plush toys, miniatures).
- **Enhanced Object Detection**: Integrate alternative models for improved main object detection accuracy.
- **Batch Processing**: Add support for processing multiple images in one run.

