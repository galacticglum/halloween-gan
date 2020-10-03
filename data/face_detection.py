"""Perform face detection on a target image."""

import cv2
import hashlib
import argparse
import tempfile
import requests
import numpy as np
from pathlib import Path
from clint.textui import progress

def download_file(url, save_filepath, chunk_size=8196):
    """Downloads a file from the specified URL."""
    request = requests.get(url, stream=True)
    with open(save_filepath, 'wb+') as file:
        total_length = int(request.headers.get('content-length'))
        expected_size = (total_length / chunk_size) + 1
        for chunk in progress.bar(request.iter_content(chunk_size=chunk_size),
                                  expected_size=expected_size,
                                  label=f'{save_filepath.name} '):
            file.write(chunk)
            file.flush()

def get_md5_from_file(filepath, chunk_size=8196):
    """Gets the MD5 hash of a file.
    Returns None if the file does not exist.
    """

    if not filepath.exists(): return

    h = hashlib.md5()
    with open(filepath, 'rb') as file:
        chunk = 0
        while chunk != b'':
            chunk = file.read(chunk_size)
            h.update(chunk)

    return h.hexdigest()

def get_default_model_files():
    """Gets the default model weight filepaths."""

    # URLs for downloading the ResNet10 SSD model for face detection.
    _DEFAULT_FILES = {
        'prototxt': {
            'md5': 'bf7a2a8de014b7b187783f1da382485c',
            'url': 'https://github.com/opencv/opencv/raw/3.4.0/samples/dnn/face_detector/deploy.prototxt',
            'save_filename': 'res10_deploy.prototxt'
        },
        'model_weights': {
            'md5': 'afbb6037fd180e8d2acb3b58ca737b9e',
            'url': 'https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel',
            'save_filename': 'res10_300x300_ssd_iter_140000.caffemodel'
        }
    }

    destination_dir = Path(tempfile.gettempdir()) / 'halloween-gan'
    destination_dir.mkdir(exist_ok=True)

    filepaths = {}
    for file_key, file in _DEFAULT_FILES.items():
        destination_filepath = destination_dir / file['save_filename']
        filepaths[file_key] = destination_filepath

        if get_md5_from_file(destination_filepath) == file['md5']: continue
        download_file(file['url'], destination_filepath)

    return filepaths['prototxt'], filepaths['model_weights']

def detect_faces(image_filepath, prototxt_filepath=None, model_weights_filepath=None, confidence_threshold=0.5):
    """Perform face detection on the input image."""

    # Load model files (if not provided)
    if prototxt_filepath is None or model_weights_filepath is None:
        filepaths = get_default_model_files()
        prototxt_filepath = filepaths[0] or prototxt_filepath
        model_weights_filepath = filepaths[1] or model_weights_filepath

    model = cv2.dnn.readNetFromCaffe(
        # We need to convert the filepaths to strings for opencv
        str(prototxt_filepath.absolute()),
        str(model_weights_filepath.absolute())
    )

    image = cv2.imread(str(image_filepath.absolute()))
    # Store the original shape of the image before resizing
    height, width = image.shape[:2]
    # Generate an input to the resnet model
    input_blob = cv2.dnn.blobFromImage(
        # The model expects a 300x300 image.
        cv2.resize(image, (300, 300)),
        scalefactor=1.0,
        size=(300, 300),
        mean=(104.0, 177.0, 123.0)
    )

    # Perform face detection with the input blob
    model.setInput(input_blob)
    output = model.forward()

    for i in range(output.shape[2]):
        confidence = output[0, 0, i, 2]
        if confidence >= confidence_threshold:
            # Compute the bounding box
            bounding_box = output[0, 0, i, 3:7] * np.array([width, height, width, height])
            x1, y1, x2, y2 = bounding_box.astype('int')

            # Draw the bounding box
            text = f'{confidence:.2f}'
            y = y1 - 10 if y1 - 10 > 10 else y1 + 10
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(image, text, (x1, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)

    cv2.imshow('Output', image)
    cv2.waitKey(0)

def main():
    """Main entrypoint when running this module from the terminal."""
    parser = argparse.ArgumentParser(description='Perform face detection on a target image.')
    parser.add_argument('image_filepath', type=Path, help='The filepath of the input image.')
    parser.add_argument('--prototxt', dest='prototxt_filepath', type=Path, default=None,
                        help='The filepath of the Caffe prototxt.')
    parser.add_argument('--model', dest='model_weights_filepath', type=Path, default=None,
                        help='The filepath of the pretrained Caffe model.')
    parser.add_argument('--confidence-threshold', type=float, default=0.5,
                        help='Minimum confidence level to consider the prediction. '
                        'Set to 0 to disable confidence filtering.')
    args = parser.parse_args()

    detect_faces(
        args.image_filepath,
        prototxt_filepath=args.prototxt_filepath,
        model_weights_filepath=args.model_weights_filepath,
        confidence_threshold=args.confidence_threshold
    )

if __name__ == "__main__":
    main()
