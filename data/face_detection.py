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
    """
    Downloads a file from the specified URL.

    :param filepath:
        The path to the file.
    :param chunk_size:
        An integer representing the number of bytes of data to get
        in a single iteration. Defaults to 8196.
    """

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
    """
    Gets the MD5 hash of a file.

    :param filepath:
        The path to the file.
    :param chunk_size:
        An integer representing the number of bytes of data to get
        in a single iteration. Defaults to 8196.
    :returns:
        The MD5 hash of the file, or None if it doesn't exist.
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

class FaceDetectionResult:
    """
    A face detected in an image.

    :ivar bounding_box:
        A tuple containing four integers representing the two
        opposite corners of the bounding box: x1, y1, x2, and y2,
        in that order, where x1 and y1 make the top-left point, and
        x2 and y2 make the bottom-left point of the bounding box.
    :ivar confidence:
        The confidence of the model prediction (from 0 to 1).
    """

    def __init__(self, bounding_box, confidence):
        """Initialize a face detection result."""
        self.bounding_box = bounding_box
        self.confidence = confidence

    def __str__(self):
        """Returns a formatted representation of this object."""
        return f'(bounding_box={self.bounding_box}, confidence={self.confidence})'

    def __repr__(self):
        """Returns an internal representation of this object."""
        return f'<FaceDetectionResult(bounding_box={self.bounding_box}, confidence={self.confidence})>'

def detect_faces(image_filepath, prototxt_filepath=None,
                 model_weights_filepath=None, confidence_threshold=0.5,
                 show_image=False):
    """
    Perform face detection on the input image.

    :param image_filepath:
        The filepath of the image to run facial detection on.
    :param prototxt_filepath:
        The filepath to the Caffe model prototxt. Defaults to None,
        meaning that the default ResNet10 SSD model prototxt is used.
    :param model_weights_filepath:
        The filepath to the Caffe model weights. Defaults to None,
        meaning that the default ResNet 10 SSD model weights are used.
    :param show_image:
        Show the image and generated bounding boxes. Defaults to False.
    :returns:
        A list of `FaceDetectionResult` objects.

    """

    image_filepath = Path(image_filepath)
    if not image_filepath.exists():
        raise FileNotFoundError(f'The file \'{image_filepath.resolve()}\' was not found!')

    # Load model files (if not provided)
    if prototxt_filepath is None or model_weights_filepath is None:
        filepaths = get_default_model_files()
        prototxt_filepath = filepaths[0] or prototxt_filepath
        model_weights_filepath = filepaths[1] or model_weights_filepath

    model = cv2.dnn.readNetFromCaffe(
        # We need to convert the filepaths to strings for opencv
        str(Path(prototxt_filepath).absolute()),
        str(Path(model_weights_filepath).absolute())
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

    result = []
    for i in range(output.shape[2]):
        confidence = output[0, 0, i, 2]
        if confidence < confidence_threshold: continue

        # Compute the bounding box
        bounding_box = output[0, 0, i, 3:7] * np.array([width, height, width, height])
        x1, y1, x2, y2 = bounding_box.astype('int')

        if show_image:
            confidence_str = f'{confidence:.4f}'
            # Draw confidence label
            cv2.putText(image, confidence_str, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), thickness=1)
            # Draw bounding box
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), thickness=1)

        result.append(FaceDetectionResult((x1, y1, x2, y2), confidence))

    if show_image:
        cv2.imshow('Output', image)
        cv2.waitKey(0)

    return result

def main():
    """Main entrypoint when running this module from the terminal."""

    parser = argparse.ArgumentParser(description='Perform face detection on a target image.')
    parser.add_argument('image_filepath', type=Path, help='The filepath of the input image.')
    parser.add_argument('--prototxt', dest='prototxt_filepath', type=Path, default=None,
                        help='The filepath of the Caffe prototxt.')
    parser.add_argument('--model', dest='model_weights_filepath', type=Path, default=None,
                        help='The filepath of the pretrained Caffe model.')
    parser.add_argument('--confidence-threshold', '-ct', type=float, default=0.5,
                        help='Minimum confidence level to consider the prediction. '
                        'Set to 0 to disable confidence filtering.')
    parser.add_argument('--show-bounding-boxes', '-sbb', action='store_true',
                        help='Show the bounding box results.')
    args = parser.parse_args()

    detect_faces(
        args.image_filepath,
        prototxt_filepath=args.prototxt_filepath,
        model_weights_filepath=args.model_weights_filepath,
        confidence_threshold=args.confidence_threshold,
        show_image=args.show_bounding_boxes
    )

if __name__ == "__main__":
    main()
