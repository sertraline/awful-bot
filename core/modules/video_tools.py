import asyncio
import subprocess
import cv2
import numpy as np
import math
import traceback
import os

from cv2 import VideoWriter, VideoWriter_fourcc
from uuid import uuid4
from datetime import datetime
from subprocess import check_output


class Executor:

    command = 'video'
    use_call_name = False

    def __init__(self, config, debugger, extractor):
        self.config = config
        self.debug = debugger
        self.extractor = extractor

    def help(self):
        return "Video tools:\n  %svideo help" % self.config.S

    def rotate(self, image, angle, switch_direction):
        (h, w) = image.shape[:2]
        center = (w / 2, h / 2)

        if not switch_direction:
            angle = -angle
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h))
        return rotated

    def animate(self, filepath, switch_direction=False):
        source = cv2.imread(filepath)
        height, width, channels = source.shape

        source = cv2.resize(source, (height//2, width//2))
        height, width, channels = source.shape

        FPS = 60
        degree = 360

        out = str(uuid4())+'.mp4'
        fourcc = VideoWriter_fourcc(*'mp4v')
        video = VideoWriter(out, fourcc, float(FPS), (width, height))

        for angle in range(degree):
            if angle % 2 == 0:
                continue
            if angle % 5 == 0:
                continue

            image_rotated = self.rotate(source, angle, switch_direction)
            resized = cv2.resize(image_rotated, (width*2, height*2))
            cent0 = image_rotated.shape[0]//2
            cent1 = image_rotated.shape[1]//2
            image_rotated = resized[cent0:cent0+height, cent1:cent1+width]
            video.write(image_rotated)

        video.release()
        return out

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

        fix_division = ", crop=trunc(iw/2)*2:trunc(ih/2)*2"
        if d == '/':
            # downscale
            scale = 'scale=iw/%d:ih/%d' % (fx, fy)
        else:
            # upscale
            scale = 'scale=iw*%d:ih*%d' % (fx, fy)
        scale_filter = scale + fix_division

        try:
            check_output(['ffmpeg', '-i', filepath, '-vf', scale_filter, out_file], timeout=240)
        except subprocess.TimeoutExpired:
            out_file = -1
        os.remove(filepath)
        return out_file

    def parse_args(self, args: list, fname: str) -> list:
        filepath = None

        if args[1] == "animate":
            switch_direction = False
            if len(args) == 3:
                if args[2] == '+':
                    switch_direction = True
            try:
                filepath = self.animate(fname, switch_direction)
            except:
                self.debug(traceback.format_exc())
                return [-1, 'An error has occured', fname]

        elif args[1] == "resize":
            self.debug('Enter resize')
            errmessg = ("Please, specify correct multipliers "
                        "fx and fy.\n"
                        "%svideo resize 2 2") % self.config.S

            if (len(args) < 4) or (len(args) > 5):
                return [-1, errmessg, fname]

            try:
                fx, fy = (float(args[2]), float(args[3]))
            except:
                return [-1, errmessg, fname]

            self.debug('Resizing video/gif')
            if len(args) == 5:
                d = args[4]
            else:
                d = '/'
            filepath = self.resize_ffmpeg(fname, fx, fy, d)
            if filepath == -1:
                return [-1, 'Timeout exceeded', fname]

        return [1, filepath]

    async def call_executor(self, event, client):
        self.debug('Enter executor of %s' % repr(self))
        args = event.raw_text.split()

        if len(args) == 1:
            return

        S = self.config.S
        if args[1] == 'help':
            self.debug("Return message for <video help>")
            await event.reply(f"Video tools:\n"
                              f"  {S}video animate [+-]\n\n"
                              f"  {S}video resize [fx] [fy] [/*]: `{S}video resize 2 2 /`\n\n"
                              )

        baseline = ['animate', 'resize']
        if not args[1] in baseline:
            self.debug("image: No functioning args found in message, ignoring")
            return

        at = datetime.now()
        fname = f"{at.year}{at.month:02}{at.day:02}_{at.hour:02}{at.minute:02}{at.second:02}"
        
        self.debug('Call download media')
        if 'animate' in args[1]:
            accept_types = ['image']
        else:
            accept_types = ['video']
        fname = await self.extractor.download_media(event, client, fname, accept_types=accept_types)
        if not fname:
            return

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.parse_args, *(args, fname))

        if len(result) == 2:
            status, filename = result
            await event.reply(file=filename, force_document=False)
            os.remove(result[1])
            self.debug("Removed: %s" % result[1])
        else:
            # error
            status, error_message, filename = result
            await event.reply(error_message)
            try:
                os.remove(filename)
                self.debug("Removed: %s" % filename)
            except OSError:
                pass
