import asyncio
import ctypes
import ctypes.util
import cv2
import os
import numpy as np
from os.path import isfile
from datetime import datetime
from scipy.ndimage import interpolation as inter


class TesseractError(Exception):
    pass


class Tesseract(object):
    _lib = None
    _api = None

    class TessBaseAPI(ctypes._Pointer):
        _type_ = type('_TessBaseAPI', (ctypes.Structure,), {})

    @classmethod
    def setup_lib(cls, lib_path=None):
        """ Create ctypes wrapper for Tesseract instead of using Python wrapper. """
        if cls._lib is not None:
            return
        if lib_path is None:
            if isfile('/usr/lib/libtesseract.so.4'):
                lib_path = '/usr/lib/libtesseract.so.4'
            else:
                lib_path = '/usr/lib/x86_64-linux-gnu/libtesseract.so.4'
        cls._lib = lib = ctypes.CDLL(lib_path)

        # source:
        # https://github.com/tesseract-ocr/tesseract/blob/95ea778745edd1cdf6ee22f9fe653b9e061d5708/src/api/capi.h

        lib.TessBaseAPICreate.restype = cls.TessBaseAPI

        lib.TessBaseAPIDelete.restype = None # void
        lib.TessBaseAPIDelete.argtypes = (cls.TessBaseAPI,) # handle

        lib.TessBaseAPIInit3.argtypes = (cls.TessBaseAPI,
                                         ctypes.c_char_p,
                                         ctypes.c_char_p)

        lib.TessBaseAPISetImage.restype = None
        lib.TessBaseAPISetImage.argtypes = (cls.TessBaseAPI,
                                            ctypes.c_void_p,
                                            ctypes.c_int,
                                            ctypes.c_int,
                                            ctypes.c_int,
                                            ctypes.c_int)

        lib.TessBaseAPISetVariable.argtypes = (cls.TessBaseAPI,
                                               ctypes.c_char_p,
                                               ctypes.c_char_p)

        lib.TessBaseAPIGetUTF8Text.restype = ctypes.c_char_p
        lib.TessBaseAPIGetUTF8Text.argtypes = (cls.TessBaseAPI,)

    def __init__(self, language='eng', datapath=None, lib_path=None):
        if self._lib is None:
            self.setup_lib(lib_path)
        self._api = self._lib.TessBaseAPICreate()
        self._lib.TessBaseAPIInit3(self._api, datapath, language.encode())

    def __del__(self):
        if not self._lib or not self._api:
            return
        if not getattr(self, 'closed', False):
            self._lib.TessBaseAPIDelete(self._api)
            self.closed = True

    def _check_setup(self):
        if not self._lib:
            raise TesseractError('lib not configured')
        if not self._api:
            raise TesseractError('api not created')

    def set_image(self, imagedata, width, height,
                  bytes_per_pixel, bytes_per_line=None):
        self._check_setup()
        if bytes_per_line is None:
            bytes_per_line = width * bytes_per_pixel
        self._lib.TessBaseAPISetImage(self._api,
                                      imagedata, width, height,
                                      bytes_per_pixel, bytes_per_line)

    def set_variable(self, key, val):
        self._check_setup()
        self._lib.TessBaseAPISetVariable(self._api, key, val)

    def get_utf8_text(self):
        self._check_setup()
        return self._lib.TessBaseAPIGetUTF8Text(self._api)

    def get_text(self):
        self._check_setup()
        result = self._lib.TessBaseAPIGetUTF8Text(self._api)
        if result:
            return result.decode('utf-8')


def convert_to_grayscale(image_data):
    return cv2.cvtColor(image_data, cv2.COLOR_BGR2GRAY)


def correct_skew(image, delta=1, limit=5):
    def determine_score(arr, angle):
        data = inter.rotate(arr, angle, reshape=False, order=0)
        histogram = np.sum(data, axis=1)
        score = np.sum((histogram[1:] - histogram[:-1]) ** 2)
        return histogram, score

    thresh = cv2.threshold(image, 0, 255,
                           cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    scores = []
    angles = np.arange(-limit, limit + delta, delta)
    for angle in angles:
        histogram, score = determine_score(thresh, angle)
        scores.append(score)

    best_angle = angles[scores.index(max(scores))]

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, best_angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), 
                             flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)

    return best_angle, rotated


def tesseract_process_image2(tess, frame_piece):
    height, width = frame_piece.frame.shape
    tess.set_image(frame_piece.frame.ctypes, width, height, 1)
    text = tess.get_utf8_text()
    return text.strip()


class FramePiece(object):
  def __init__(self, img, whitelist):
    self.frame = img
    self.whitelist = whitelist if whitelist else \
                    ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                     "abcdefghijklmnopqrstuvwxyz1234567890")
    self.psm = 4


class Executor():
    
    LANG_LIST = [
             'eng',
             'rus',
             'fra',
             'jav',
             'ell',
             'hin',
             'ita',
             'chi',
             'san',
             'pol',
             'ukr',
             'deu',
             'ara',
             'spa'
            ]

    command = 'ocr_'
    # placeholders: list of all values you expect to see in the beginning of command
    placeholders = [lang for lang in LANG_LIST]
    use_call_name = False

    def __init__(self, config, debugger, extractor):
        self.config = config
        self.debug = debugger
        self.extractor = extractor

    def help(self):
        langlist = str(self.LANG_LIST).replace("'", "")
        return ("OCR:\nReply or send media with !ocr_eng command\n"
                f"Language list:\n  {langlist}\n"
                 "Reply to any image with command to OCR it.")

    def img_ocr(self, image_path : str, command : str) -> str:
        command = command.split('_')
        if len(command) < 2:
            return
        tlang = None
        for tl in self.LANG_LIST:
            if tl == command[1]:
                tlang = tl
                break
        if not tlang:
            return
        if tlang == 'chi':
            tlang = 'chi_sim'
        image = cv2.imread(image_path)
        self.debug(f"Loaded image: {image_path}")

        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        if image.shape[0] < 1000:
            self.debug("Resizing...")
            image = cv2.resize(image, None, fx=2.0, fy=2.0)

        angle, image = correct_skew(image)

        self.debug(f"Image angle: {angle}")
        self.debug(f"Language: {tlang}")

        tess = Tesseract(language=tlang)

        frame_piece = FramePiece(image, None)
        self.debug("Processing image...")
        d = tesseract_process_image2(tess, frame_piece)
        d = d.decode()
        return d

    async def call_executor(self, event, client):
        dtt = datetime.now()
        fname = f"{dtt.year}-{dtt.month:02}-{dtt.day:02} {dtt.hour}:{dtt.minute}:{dtt.second}"
        fname = await self.extractor.download_media(event, client, fname)
        if not fname:
            return
        loop = asyncio.get_event_loop()
        ocr = await loop.run_in_executor(None, self.img_ocr, *(fname, event.raw_text[:8]))
        if ocr:
            await event.reply(str(ocr))
        os.remove(fname)
