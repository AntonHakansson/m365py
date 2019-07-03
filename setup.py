from setuptools import setup

setup(
    name='m365py',
    url='https://github.com/AntonHakansson/m365py',
    author='Anton Håkansson',
    author_email='anton.hakansson98@@gmail.com',
    packages=['m365py'],
    install_requires=['bluepy'],
    version='0.1',
    license='MIT',
    description='A library to receive parsed BLE Xiaomi M365 scooter(Version=V1.3.8) messages using bluepy',
    # TODO:
    # long_description=open('README.md').read(),
)
