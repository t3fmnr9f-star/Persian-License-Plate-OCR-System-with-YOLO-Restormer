from ultralytics import YOLO


if __name__ == '__main__':
    model = YOLO('yolo11l-seg.pt')
    model.train(data='dataset\dataset.yaml', epochs=90, batch=24, imgsz=1180, device='cuda', workers=1, patience=10, cache=True)

