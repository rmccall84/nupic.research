# HTM for MNIST

This example shows how to use an HTM network to classify images from the
MNIST dataset. See the README.md file in mnist_extraction_source for more
details on the dataset.

## Instructions

1. Download and extract the MNIST data:

    ```
    ./extract_mnist.sh
    ```

2. Move extracted data:

    ```
    mkdir mnist
    mv mnist_extraction_source/training mnist/
    mv mnist_extraction_source/testing mnist/
    ```

3. Convert the resulting individual text files (one
    file per training/testing sample) into a NuPIC-compatible
    image format (in this case, PNG images):

    ```
    python ./convertImages.py mnist
    ```

    The result will be a set of 70,000 PNG-format images
    organized by category (0 through 9) and partitioned into
    60,000 training images and 10,000 testing images.

4. Create a small training validation set:

    ```
    ./create_training_sample.sh
    ```

5. Train and test an HTM network:

    ```
    python run_mnist_experiment.py
    ```

## Results

This example achieves 95.56% accuracy on the 10,000 image training set as
of 2015-04-13.
