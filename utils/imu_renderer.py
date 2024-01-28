"""Imu viewer, install python3-pygame and python3-opengl"""
import json
import time

import pygame
from OpenGL.raw.GLU import gluPerspective
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLUT import *

import redis


class ImuViewer:

    def __init__(self):
        pygame.init()
        self.display = (1000, 800)
        pygame.display.set_mode(self.display, DOUBLEBUF | OPENGL)
        pygame.display.set_caption("IMU Viewer")

        self._camera_setup()

        self.vertices = self._define_mesh()
        self.edges = self._define_edges()
        self.surfaces = self._define_surfaces()
        self.colors = self._define_colors()

        self.roll = 0
        self.pitch = 0
        self.yaw = 0

    def _camera_setup(self):
        gluPerspective(45, (self.display[0] / self.display[1]), 0.1, 50.0)
        glTranslatef(-.5, 0.0, -7)

    @staticmethod
    def _define_mesh():
        return (
            (1, -0.5, -1.5),  # 0
            (1, 0.5, -1.5),  # 1
            (-1, 0.5, -1.5),  # 2
            (-1, -0.5, -1.5),  # 3
            (1, -0.5, 1.5),  # 4
            (1, 0.5, 1.5),  # 5
            (-1, -0.5, 1.5),  # 6
            (-1, 0.5, 1.5)  # 7
        )

    @staticmethod
    def _define_edges():
        return (
            (0, 1),  # 0
            (0, 3),  # 1
            (0, 4),  # 2
            (2, 1),  # 3
            (2, 3),  # 4
            (2, 7),  # 5
            (6, 3),  # 6
            (6, 4),  # 7
            (6, 7),  # 8
            (5, 1),  # 9
            (5, 4),  # 10
            (5, 7)  # 11
        )

    @staticmethod
    def _define_surfaces():
        return (
            (0, 1, 2, 3),  # 0
            (3, 2, 7, 6),  # 1
            (6, 7, 5, 4),  # 2
            (4, 5, 1, 0),  # 3
            (1, 5, 7, 2),  # 4
            (4, 0, 3, 6)  # 5
        )

    @staticmethod
    def _define_colors():
        return (
            (1, 0, 0),  # 0
            (0, 1, 0),  # 1
            (0, 0, 1),  # 2
            (0, 1, 0),  # 3
            (1, 1, 1),  # 4
            (0, 1, 1),  # 5
            (1, 0, 0),  # 6
            (0, 1, 0),  # 7
            (0, 0, 1),  # 8
            (1, 0, 0),  # 9
            (1, 1, 1),  # 10
            (0, 1, 1),  # 11
        )

    def _render(self):
        # Clear
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Surfaces
        glBegin(GL_QUADS)
        for surface in self.surfaces:
            x = 0
            for vertex in surface:
                x += 1
                glColor3fv(self.colors[x])
                glVertex3fv(self.vertices[vertex])
        glEnd()

        # Edges
        glBegin(GL_LINES)
        for edge in self.edges:
            for vertex in edge:
                glVertex3fv(self.vertices[vertex])

        glEnd()

        # Render
        pygame.display.flip()

    def set_orientation(self, roll, pitch, yaw):
        roll_offset = roll - self.roll
        pitch_offset = pitch - self.pitch
        yaw_offset = yaw - self.yaw

        glRotatef(roll_offset, 0, 0, 1)
        glRotatef(pitch_offset, 1, 0, 0)
        glRotatef(yaw_offset, 0, 1, 0)

        # update roll but keep it between -180 and 180
        self.roll = roll
        if self.roll > 180:
            self.roll -= 360
        elif self.roll < -180:
            self.roll += 360

        # update pitch but keep it between -180 and 180
        self.pitch = pitch
        if self.pitch > 180:
            self.pitch -= 360
        elif self.pitch < -180:
            self.pitch += 360

        # update yaw but keep it between -180 and 180
        self.yaw = yaw
        if self.yaw > 180:
            self.yaw -= 360
        elif self.yaw < -180:
            self.yaw += 360

        self._render()


viewer = ImuViewer()
r = redis.Redis(host='rpi2.dace-alpha.ts.net', port=6379, db=0)

while True:
    data = json.loads(r.get('sensors:sense_hat:data'))
    viewer.set_orientation(data['roll'], data['pitch'], data['yaw'])
    time.sleep(0.01)
