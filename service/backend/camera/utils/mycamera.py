from .functions import *
from common.types import *
from common.utils import Singleton

from ..assets import storeConfig

import os
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

from typing import Dict

from PIL import Image as PILImage
from picamera2 import Picamera2, Preview


class MyCamera(metaclass=Singleton):
    def __init__(self):
        """
        video : 현재 저장되고 있는 영상!
        """
        self._video:Video = None
        self._camera = Picamera2()
        self._configure_camera()
        self._camera.start()

    def __del__(self):
        self._camera.close()

    def _configure_camera(self):
        self._camera.start_preview(Preview.NULL)
        config = self._camera.create_still_configuration()
        config['buffer_count'] = 5
        self._camera.configure(config)
    
    @property
    def video(self):
        return self._video

    async def start_video(self, title:str, width:float, height:float)->None:
        """
        video를 새로 지정하고, 해당 비디오와 동일한 구성요소가 디스크에 있으면 지운다.
        """
        self._video = Video(mode="RGBA", title=title, format="jpeg", duration={"start":datetime.now(), "end":datetime.now()}, width=width, height=height, frames=[])
        
        if (storeConfig['paths']['frames'] / title).exists():
            shutil.rmtree(storeConfig['paths']['frames'] / title)
        
        if (storeConfig['paths']['videos'] / title).exists():
            shutil.rmtree(storeConfig['paths']['videos'] / title)

        os.makedirs(storeConfig['paths']['frames'] / title, exist_ok=False)
        return None


    async def end_video(self, savedTitle:str) -> None:
        """
        Video 저장하기
        """
        subprocess.run(['mv', storeConfig['paths']['frames'] / self.video.title, storeConfig['paths']['frames'] / savedTitle])
        
        self.video.title = savedTitle
        self.video.duration["end"] = datetime.now()

        with open(storeConfig['paths']['videos'] / f"{savedTitle}.json", "w") as fd:
            fd.write(self.video.json())
        return None


    async def capture(self)->Image:
        """
        사진을 찍고 Image로 반환!
        """
        frame = Frame(id=len(self.video.frames) + 1, captured=datetime.now())
        img:PILImage = self._camera.capture_image().resize([self.video.width, self.video.height], PILImage.Resampling.NEAREST)
        bytesImg = await make_bytes_from_img(img)
        img.close()

        self.video.frames.append(frame)
        return Image(captured=frame.captured, width=self.video.width, height=self.video.height, risked=[], src=self.video.title, id=frame.id, data=bytesImg)
        
    async def save_frame(self, image:Image) -> bool:
        """
        이미지 저장!
        """
        try:
            name = await make_frame_name(self.video, image.id)
            img = await make_img_from_bytes(image.data, self.video.width, self.video.height)
            img.save(name)
            return True
        except Exception as e:
            print(e)
            return False

    async def get_frame(self, id: int)->Image:
        """
        Video의 특정 프레임 이미지 가져오기!
        """
        imgPath:Path = await make_frame_name(self.video, id)
        if not imgPath.exists():
            raise FileNotFoundError
        else:
            img = PILImage.open(imgPath).resize([self.video.width, self.video.height], PILImage.Resampling.BICUBIC)
            data = make_bytes_from_img(img)
            img.close()
            return Image(captured=self.video.frames[id].captured, width=self.video.width, height=self.video.height, risked=[], src=self.video.title, id = id, data=data)
        