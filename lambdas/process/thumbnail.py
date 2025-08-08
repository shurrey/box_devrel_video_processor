import os
import io
import base64
import logging
from typing import Union, Optional, Tuple
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
import cv2
from rembg import remove, new_session
import random

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ThumbnailProcessor:
    """
    Professional thumbnail processor optimized for AWS Lambda.
    Extracts person from video frames with transparent background.
    """
    
    def __init__(self, model_name: str = 'u2net'):
        """
        Initialize with specified model.
        
        Args:
            model_name: rembg model ('u2net', 'u2net_human_seg', 'silueta')
        """
        self.model_name = model_name
        self.session = None
        self._initialize_session()
    
    def _initialize_session(self):
        """Initialize rembg session with error handling."""
        try:
            # Force CPU provider to avoid CoreML permission issues on macOS
            providers = ['CPUExecutionProvider']
            self.session = new_session(self.model_name, providers=providers)
            logger.info(f"Initialized rembg session with model: {self.model_name} using CPU provider")
        except Exception as e:
            logger.error(f"Failed to initialize rembg session: {str(e)}")
            raise
    
    def process_image(self, 
                     input_data: Union[bytes, str, Image.Image], 
                     enhance_quality: bool = True,
                     preserve_original_lighting: bool = True,
                     target_size: Optional[Tuple[int, int]] = None) -> bytes:
        """
        Process image to extract person with transparent background.
        
        Args:
            input_data: Image as bytes, base64 string, file path, or PIL Image
            enhance_quality: Apply professional enhancement for thumbnails
            preserve_original_lighting: Keep original lighting and colors (recommended)
            target_size: Optional resize target (width, height)
        
        Returns:
            PNG image bytes with transparent background
        """
        try:
            # Load and validate image
            original_image = self._load_image(input_data)
            
            # Keep original for lighting preservation
            if preserve_original_lighting:
                # Create enhanced version for segmentation only
                segmentation_image = self._enhance_input(original_image) if enhance_quality else original_image
                
                # Resize both versions if needed
                if target_size:
                    original_image = self._smart_resize(original_image, target_size)
                    segmentation_image = self._smart_resize(segmentation_image, target_size)
                
                # Remove background using enhanced version for better segmentation
                mask_image = self._remove_background(segmentation_image)
                
                # Apply the mask to the original image to preserve lighting
                output_image = self._apply_mask_to_original(original_image, mask_image)
                
                # Minimal post-processing that preserves lighting
                if enhance_quality:
                    output_image = self._enhance_output(output_image, preserve_lighting=True)
            else:
                # Original behavior for backward compatibility
                image = original_image
                if enhance_quality:
                    image = self._enhance_input(image)
                
                if target_size:
                    image = self._smart_resize(image, target_size)
                
                output_image = self._remove_background(image)
                
                if enhance_quality:
                    output_image = self._enhance_output(output_image, preserve_lighting=False)
            
            # Convert to bytes
            return self._image_to_bytes(output_image)
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise
    
    def _load_image(self, input_data: Union[bytes, str, Image.Image]) -> Image.Image:
        """Load image from various input formats."""
        if isinstance(input_data, Image.Image):
            return input_data.convert('RGB')
        
        elif isinstance(input_data, bytes):
            return Image.open(io.BytesIO(input_data)).convert('RGB')
        
        elif isinstance(input_data, str):
            # Check if it's base64 or file path
            if input_data.startswith('data:image/') or len(input_data) > 100:
                # Assume base64
                if 'base64,' in input_data:
                    input_data = input_data.split('base64,')[1]
                image_bytes = base64.b64decode(input_data)
                return Image.open(io.BytesIO(image_bytes)).convert('RGB')
            else:
                # Assume file path
                return Image.open(input_data).convert('RGB')
        
        else:
            raise ValueError(f"Unsupported input type: {type(input_data)}")
    
    def _enhance_input(self, image: Image.Image) -> Image.Image:
        """Enhance input image for better segmentation results."""
        # Convert to numpy for OpenCV operations
        img_array = np.array(image)
        
        # Improve contrast and brightness for better person detection
        lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # Merge back
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)
        
        return Image.fromarray(enhanced)
    
    def _smart_resize(self, image: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
        """Smart resize maintaining aspect ratio and quality."""
        width, height = image.size
        target_width, target_height = target_size
        
        # Calculate aspect ratio
        aspect = width / height
        target_aspect = target_width / target_height
        
        if aspect > target_aspect:
            # Image is wider than target
            new_width = target_width
            new_height = int(target_width / aspect)
        else:
            # Image is taller than target
            new_height = target_height
            new_width = int(target_height * aspect)
        
        # Use high-quality resampling
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def _remove_background(self, image: Image.Image) -> Image.Image:
        """Remove background using rembg."""
        if not self.session:
            raise RuntimeError("rembg session not initialized")
        
        # Convert PIL Image to bytes for rembg
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        input_bytes = img_byte_arr.getvalue()
        
        # Remove background
        output_bytes = remove(input_bytes, session=self.session)
        
        # Convert back to PIL Image
        return Image.open(io.BytesIO(output_bytes))
    
    def _apply_mask_to_original(self, original_image: Image.Image, mask_image: Image.Image) -> Image.Image:
        """Apply the alpha mask from segmentation to the original image to preserve lighting."""
        # Ensure original is RGB and mask has alpha
        if original_image.mode != 'RGB':
            original_image = original_image.convert('RGB')
        
        if mask_image.mode != 'RGBA':
            mask_image = mask_image.convert('RGBA')
        
        # Extract the alpha channel from the mask
        alpha = mask_image.split()[-1]
        
        # Combine original RGB with the extracted alpha mask
        result = Image.merge('RGBA', (*original_image.split(), alpha))
        
        return result
    
    def _enhance_output(self, image: Image.Image, preserve_lighting: bool = True) -> Image.Image:
        """Enhance output image for professional thumbnail quality."""
        # Ensure image has alpha channel
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Extract alpha channel for processing
        alpha = image.split()[-1]
        
        # Smooth edges of the mask
        alpha = alpha.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        # Extract RGB channels
        rgb = Image.merge('RGB', image.split()[:3])
        
        # Only enhance RGB if not preserving original lighting
        if not preserve_lighting:
            # Apply original enhancement for backward compatibility
            enhancer = ImageEnhance.Color(rgb)
            rgb = enhancer.enhance(1.1)  # 10% more saturation
            
            enhancer = ImageEnhance.Sharpness(rgb)
            rgb = enhancer.enhance(1.1)  # 10% more sharpness
        
        # Merge back with processed alpha (alpha smoothing is always beneficial)
        return Image.merge('RGBA', (*rgb.split(), alpha))
    
    def _image_to_bytes(self, image: Image.Image, format: str = 'PNG') -> bytes:
        """Convert PIL Image to bytes."""
        img_byte_arr = io.BytesIO()
        
        # Optimize PNG for smaller file size
        if format.upper() == 'PNG':
            image.save(img_byte_arr, 
                      format=format, 
                      optimize=True, 
                      compress_level=6)
        else:
            image.save(img_byte_arr, format=format, quality=95)
        
        return img_byte_arr.getvalue()


def extract_person_thumbnail(input_data: Union[bytes, str], 
                           target_size: Optional[Tuple[int, int]] = (1280, 720),
                           model: str = 'u2net',
                           preserve_original_lighting: bool = True) -> bytes:
    """
    Convenience function to extract person from image with transparent background.
    Optimized for YouTube thumbnail creation from video frames.
    
    Args:
        input_data: Image as bytes or base64 string
        target_size: Target size for thumbnail (width, height). Default: 1280x720
        model: rembg model to use ('u2net', 'u2net_human_seg', 'silueta')
        preserve_original_lighting: Keep original lighting/colors (recommended for natural look)
    
    Returns:
        PNG image bytes with transparent background
    
    Example:
        # For natural lighting (recommended)
        result_bytes = extract_person_thumbnail(
            input_data=image_bytes,
            target_size=(1920, 1080),
            preserve_original_lighting=True
        )
        
        # For enhanced/brighter look (original behavior)
        result_bytes = extract_person_thumbnail(
            input_data=image_bytes,
            target_size=(1920, 1080),
            preserve_original_lighting=False
        )
    """
    processor = ThumbnailProcessor(model_name=model)
    return processor.process_image(
        input_data=input_data,
        enhance_quality=True,
        preserve_original_lighting=preserve_original_lighting,
        target_size=target_size
    )

def get_random_video_frame(video_path):
    """
    Extracts and saves a random frame from a video file.

    Args:
        video_path (str): The path to the video file.
        output_filename (str): The desired filename for the saved frame image.
                               Defaults to "random_frame.jpg".
    Returns:
        bool: True if a frame was successfully extracted and saved, False otherwise.
    """
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"Error: Could not open video file at {video_path}")
        return False

    # Get the total number of frames in the video
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    

    if total_frames == 0:
        print("Error: Video contains no frames.")
        cap.release()
        return False

    # Calculate the number of frames in the first 30 seconds
    duration = 10
    max_frame = min(int(fps * duration), total_frames)

    # Choose a random frame index
    random_frame_index = random.randint(0, max_frame - 1)

    # Set the video capture position to the random frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame_index)

    # Read the frame
    ret, frame = cap.read()

    file_name = video_path.split("/")[-1]

    output_filename = f"/tmp/{file_name}_frame_{random_frame_index}.jpg"

    if ret:
        # Save the frame as an image
        cv2.imwrite(output_filename, frame)
        print(f"Successfully extracted and saved frame {random_frame_index} as {output_filename}")
        cap.release()
        return output_filename
    else:
        print(f"Error: Could not read frame {random_frame_index}.")
        cap.release()
        return None