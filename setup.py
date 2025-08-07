import setuptools

cdk_ver = "2.117.0"

with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="Box DevRel Video Processor",
    version="0.0.1",

    description="Transcribe videos from Box via Box Skills and process for YouTube.",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="Scott Hurrey",

    package_dir={"": "box_devrel_video_processor"},
    packages=setuptools.find_packages(where="box_devrel_video_processor"),

    install_requires=[
        "aws-cdk-lib",
        "aws-cdk.aws-lambda-python-alpha",
        "constructs",
        "boto3",
        "boxsdk",
        "box_sdk_gen"
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: Apache Software License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
