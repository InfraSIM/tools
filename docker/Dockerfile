# Use an official Python runtime as a base image
FROM ubuntu:16.04

# Set the working directory to /app
WORKDIR /infrasim-compute

# Copy the current directory contents into the container at /app
ADD . /infrasim-compute


# Install dependency
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y build-essential libssl-dev libffi-dev python-dev libaio-dev bridge-utils git apt-utils
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y net-tools libnuma-dev libglib2.0-dev libapt-pkg5.0 iputils-ping isc-dhcp-client

# Upgrade pip and install setuptools
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y python-pip
RUN pip install --upgrade pip
RUN pip install setuptools

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV DEBIAN_FRONTEND noninteractive

# Run app.py when the container launches
RUN ["python", "setup.py", "install"]

# RUN which infrasim
RUN ["infrasim", "init"]

