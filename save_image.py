from comfy.cli_args import args
import folder_paths
import json
import numpy
import os
from PIL import Image, ExifTags
from PIL.PngImagePlugin import PngInfo
import uuid
from io import BytesIO
import time

class SaveImagePlus:
    def __init__(self):
        pass

    FILE_TYPE_PNG = "PNG"
    FILE_TYPE_JPEG = "JPEG"
    FILE_TYPE_WEBP_LOSSLESS = "WEBP (lossless)"
    FILE_TYPE_WEBP_LOSSY = "WEBP (lossy)"
    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "image"

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "filename_prefix": ("STRING", {"default": "%uuid%"}),
                "file_type": ([s.FILE_TYPE_JPEG, s.FILE_TYPE_PNG, s.FILE_TYPE_WEBP_LOSSLESS, s.FILE_TYPE_WEBP_LOSSY], ),
                "remove_metadata": ("BOOLEAN", {"default": False}),
                "quality": ("INT", {"default": 80, "min": 1, "max": 100}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    def save_images(self, images, filename_prefix="%uuid%", file_type=FILE_TYPE_JPEG, remove_metadata=False, quality=80, prompt=None, extra_pnginfo=None):
        if filename_prefix == "%uuid%":
            filename_prefix = str(uuid.uuid4()).replace('-', '')

        output_dir = folder_paths.get_output_directory()
        full_output_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(filename_prefix, output_dir, images[0].shape[1], images[0].shape[0])
        extension = {
            self.FILE_TYPE_PNG: "png",
            self.FILE_TYPE_JPEG: "jpg",
            self.FILE_TYPE_WEBP_LOSSLESS: "webp",
            self.FILE_TYPE_WEBP_LOSSY: "webp",
        }.get(file_type, "jpg")

        results = []
        for image in images:
            array = 255. * image.cpu().numpy()
            img = Image.fromarray(numpy.clip(array, 0, 255).astype(numpy.uint8))

            kwargs = dict()
            if extension == "png":
                kwargs["compress_level"] = 4
                if not remove_metadata and not args.disable_metadata:
                    metadata = PngInfo()
                    if prompt is not None:
                        metadata.add_text("prompt", json.dumps(prompt))
                    if extra_pnginfo is not None:
                        for x in extra_pnginfo:
                            metadata.add_text(x, json.dumps(extra_pnginfo[x]))
                    kwargs["pnginfo"] = metadata
            else:
                if file_type == self.FILE_TYPE_WEBP_LOSSLESS:
                    kwargs["lossless"] = True
                else:
                    kwargs["quality"] = quality
                if not remove_metadata and not args.disable_metadata:
                    metadata = {}
                    if prompt is not None:
                        metadata["prompt"] = prompt
                    if extra_pnginfo is not None:
                        metadata.update(extra_pnginfo)
                    exif = img.getexif()
                    exif[ExifTags.Base.UserComment] = json.dumps(metadata)
                    kwargs["exif"] = exif.tobytes()

            timestamp = int(time.time() * 1000)
            file = f"{filename}_{timestamp}_{counter:03}.{extension}"
            
            if extension == "jpg":
                buffer = BytesIO()
                # optimize: Enables additional optimization to reduce file size
                # progressive: Saves the image in a progressive format, allowing partial loading in web browsers
                img.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
                with open(os.path.join(full_output_folder, file), "wb") as f:
                    f.write(buffer.getvalue())
            else:
                img.save(os.path.join(full_output_folder, file), **kwargs)
            
            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": "output",
            })
            counter += 1

        return { "ui": { "images": results } }

NODE_CLASS_MAPPINGS = {
    "SaveImagePlus": SaveImagePlus
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImagePlus": "Save Image Plus"
}

WEB_DIRECTORY = "web"
