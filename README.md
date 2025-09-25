# Powerful Iranian License Plate Reader System

**This system works even on very blurry license plates**

The pipeline follows a multi-stage architecture:

1. **YOLOv11** for license plate detection and segmentation  
2. A robust module for precise cropping and automatic **perspective correction**  
3. **Restormer** for enhancing plate image quality (deblurring, denoising, low-light correction)  
4. Custom **OCR module** for accurate character recognition under real-world conditions

Unlike most OCR systems that perform recognition directly on raw images, this system first **enhances** the plate quality — resulting in significantly higher accuracy, even with blurry, angled, or low-light images.



A few examples of the model's performance:

<img src="Screenshot 2025-07-26 210210.png" width="600"/>
<img src="Screenshot 2025-07-26 210453.png" width="600"/>
---



This system, with 4 Al models together, offers much better performance than previous license plate reader systems. Because it first de-blurs the license plate and then performs OCR on it.
This system is currently capable of being deployed in CCTV cameras across the country as the main license plate reader software.
This system is fully usable in organizations that improve the quality of license plate images.

I completed the entire process of this project, from training the models to its implementation, in about 4 months.
What I did:
. Creating a roadmap and choosing the right technology for this task
. Collecting datasets and training the yolo and restormer models
. Creating a gui
. Final implementation, and taking steps to sell this system



### 🔧 Technologies Used
- PyTorch
- YOLO
- Restormer  
- PyQt5

### 📌 Use Cases
- Traffic surveillance  
- Smart parking  
- Police enforcement  
- Urban monitoring  
