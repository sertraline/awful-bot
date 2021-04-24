import asyncio
import cv2
import os
import sys

from PIL import Image
from datetime import datetime
from subprocess import check_output


class Executor:

    command = 'image'
    use_call_name = False

    def __init__(self, config, debugger, extractor):
        self.config = config
        self.debug = debugger
        self.extractor = extractor

    def help(self):
        return "Image tools:\n  %simage help" % self.config.S

    def grayscale(self, filepath: str) -> str:
        """
        Convert to grayscale.
        Return filepath to grayscale image.
        """
        image = cv2.imread(filepath)
        self.debug("Loaded image: %s" % filepath)

        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        cv2.imwrite(filepath, image)
        self.debug("Write the result (grayscale) to %s" % filepath)
        return filepath

    def rotate(self, filepath: str, degree: int) -> str:
        """
        Rotate image based on degree.
        Return filepath to rotated image.
        """
        image = cv2.imread(filepath)
        self.debug("Loaded image: %s" % filepath)

        height, width = image.shape[:2]
        image_center = (width/2, height/2)

        rotation_mat = cv2.getRotationMatrix2D(image_center, degree, 1.)

        # rotation calculates the cos and sin, taking absolutes of those.
        abs_cos = abs(rotation_mat[0, 0])
        abs_sin = abs(rotation_mat[0, 1])

        # find the new width and height bounds
        bound_w = int(height * abs_sin + width * abs_cos)
        bound_h = int(height * abs_cos + width * abs_sin)

        # subtract old image center 
        # and adding the new image center coordinates
        rotation_mat[0, 2] += bound_w/2 - image_center[0]
        rotation_mat[1, 2] += bound_h/2 - image_center[1]

        # rotate image with the new bounds and translated rotation matrix
        rotated_mat = cv2.warpAffine(image, rotation_mat, (bound_w, bound_h))
        height, width = rotated_mat.shape[:2]

        new_h = None
        new_w = None
        # Resize image if it is too large.
        # Avoid outofmemory error and bad usage patterns
        if height > 4000 or width > 4000:
            new_h, new_w = (height//2, width//2)

        if new_w:
            rotated_mat = cv2.resize(rotated_mat, (new_w, new_h))

        cv2.imwrite(filepath, rotated_mat)
        self.debug(f"Write the result (rotate) to {filepath}")
        return filepath

    def flip(self, filepath: str, mode: str) -> str:
        """
        Flip image vertically or horizontally.
        """

        image = cv2.imread(filepath)
        self.debug("Loaded image: %s" % filepath)

        if mode.startswith("h"):
            image = cv2.flip(image, 0)
        else:
            image = cv2.flip(image, 1)

        cv2.imwrite(filepath, image)
        self.debug("Write the result (flip) to %s" % filepath)
        return filepath

    def resize_ffmpeg(self, filepath: str, fx: float, fy: float, d='/') -> str:
        """
        Resize video to given aspect ratio using ffmpeg.
        """
        out_file = 'resized_'+filepath
        fx, fy = int(fx), int(fy)
        if fx > 4:
            fx = 4
        if fy > 4:
            fy = 4

        fix_division = ", pad=ceil(iw/2)*2:ceil(ih/2)*2"
        if d == '/':
            # downscale
            scale = 'scale=iw/%d:ih/%d' % (fx, fy) 
        else:
            # upscale
            scale = 'scale=iw*%d:ih*%d' % (fx, fy)
        scale_filter = scale + fix_division

        result = check_output(['ffmpeg', '-i', filepath, '-vf', scale_filter, out_file])
        os.remove(filepath)
        return out_file


    def resize(self, filepath: str, fx: float, fy: float, method=None) -> str:
        """
        Resize image based on horizontal (fx) and vertical (fy)
        multipliers.
        Apply interpolation if specified.
        Return filepath to resized image.
        """

        # set resize limit
        # (avoid OutOfMemory error)
        if fx > 10:
            self.debug("Lowering fx=%d to 10" % fx)
            fx = 10
        if fy > 10:
            self.debug("Lowering fy=%d to 10" % fy)
            fy = 10

        image = cv2.imread(filepath)
        self.debug("Loaded image: %s" % filepath)

        if image.shape[0] > 2080:
            # lower the limit for bigger images
            if fx >= 10:
                self.debug("Lowering fx=%d to 4" % fx)
                fx = 4
            if fy >= 10:
                self.debug("Lowering fy=%d to 4" % fy)
                fy = 4

        inters = {
            'cubic': cv2.INTER_CUBIC,
            'linear': cv2.INTER_LINEAR,
            'lanczos': cv2.INTER_LANCZOS4,
            'nearest': cv2.INTER_NEAREST
        }

        if method:
            for key in inters.keys():
                if method == key:
                    break
            image = cv2.resize(image, None, fx=fx, fy=fy, interpolation=inters[key])
        else:
            image = cv2.resize(image, None, fx=fx, fy=fy)

        cv2.imwrite(filepath, image)
        self.debug("Write the result (resize) to %s" % filepath)
        return filepath

    def denoise(self, filepath: str, filter_strength: int) -> str:
        """
        Apply denoising filter.
        If filter strength is not specified, use defaults (13).
        Higher value removes more image details.
        Return filepath to denoised image.
        """
        image = cv2.imread(filepath)
        self.debug("Loaded image: %s" % filepath)

        if len(image.shape) < 3:
            image = cv2.fastNlMeansDenoisingColored(image, None, h=filter_strength,
                                                    templateWindowSize=14, searchWindowSize=21)
        else:
            image = cv2.fastNlMeansDenoising(image, None, h=filter_strength,
                                             templateWindowSize=14, searchWindowSize=21)

        cv2.imwrite(filepath, image)
        self.debug("Write the result (denoise) to %s" % filepath)
        return filepath

    def parse_args(self, args: list, fname: str) -> list:

        if args[1] == "grayscale":
            filepath = self.grayscale(fname)

        elif args[1] == "flip":
            errmessg = ("Please, specify mode.\n"
                        "v, h = vertical, horizontal\n"
                        "%simage flip v\n"
                        "%simage flip h") % (self.config.S, self.config.S)

            if (len(args) < 3) or (len(args) > 3):
                return [-1, errmessg, fname]

            mode = args[2]
            filepath = self.flip(fname, mode)

        elif args[1] == "rotate":
            errmessg = ("Please, specify a degree.\n"
                        "%simage rotate 45") % self.config.S

            if (len(args) < 3) or (len(args) > 3):
                return [-1, errmessg, fname]

            if len(args) == 3:
                try:
                    degree = int(args[2])
                except:
                    return [-1, errmessg, fname]
                filepath = self.rotate(fname, degree)

        elif args[1] == "resize":
            self.debug('Enter resize')
            errmessg = ("Please, specify correct multipliers "
                        "fx and fy.\n"
                        "%simage resize 2 2") % self.config.S

            if (len(args) < 4) or (len(args) > 5):
                return [-1, errmessg, fname]

            try:
                fx, fy = (float(args[2]), float(args[3]))
            except:
                return [-1, errmessg, fname]

            if fname.endswith('.mp4'):
                self.debug('Resizing video/gif')
                if len(args) == 5:
                    d = args[4]
                else:
                    d = '/'
                filepath = self.resize_ffmpeg(fname, fx, fy, d)
            elif len(args) == 4:
                self.debug('Resizing image %f/%f' % (fx, fy))
                filepath = self.resize(fname, fx, fy)
            elif len(args) == 5:
                self.debug('Resizing image %f/%f/%s' % (fx, fy, args[4]))
                filepath = self.resize(fname, fx, fy, args[4])

        elif args[1] == "denoise":
            if len(args) == 2:
                filepath = self.denoise(fname, 13)
            elif len(args) == 3:
                try:
                    filt_st = int(args[2])
                except:
                    return [-1,
                            ("Please, specify correct filter "
                             "strength (int)\n"
                             "%simage denoise 21") % self.config.S,
                            fname
                            ]
                filepath = self.denoise(fname, filt_st)

        return [1, filepath]

    async def call_executor(self, event, client):
        self.debug('Enter executor of %s' % repr(self))
        args = event.raw_text.split()

        if len(args) == 1:
            return

        S = self.config.S
        if args[1] == 'help':
            self.debug("Return message for <image help>")
            await event.reply(f"Image tools:\n"
                              f"  {S}image grayscale\n\n"
                              f"  {S}image rotate [degree]: `{S}image rotate 90`\n\n"
                              f"  {S}image resize [fx] [fy] [interpolation]:\n"
                              f"      `{S}image resize 2.5 2.5 linear`\n"
                              f"      `{S}image resize 2 2`\n"
                              f"      interpolation: __cubic, linear, lanczos, nearest__\n\n"
                              f"  {S}image denoise [filter_strength]: `{S}image denoise 13`\n\n"
                              f"  {S}image flip [v|h]: `{S}image flip h`"
                              )

        baseline = ['grayscale', 'rotate', 'resize', 'denoise', 'flip']
        if not args[1] in baseline:
            self.debug("image: No functioning args found in message, ignoring")
            return

        at = datetime.now()
        fname = f"{at.year}{at.month:02}{at.day:02}_{at.hour:02}{at.minute:02}{at.second:02}"
        
        self.debug('Call download media')
        fname = await self.extractor.download_media(event, client, fname)
        if not fname:
            return

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.parse_args, *(args, fname))

        if result[0] == 1:
            if result[1].endswith('mp4'):
                force_document = False
            else:
                force_document = bool('resize' in args[1] or 'denoise' in args[1]) 
            await event.reply(file=result[1], force_document=force_document)
            # force_document: no compression
            os.remove(result[1])
            self.debug("Removed: %s" % result[1])
        else:
            # error
            await event.reply(result[1])
            os.remove(result[2])
            self.debug("Removed: %s" % result[2])
