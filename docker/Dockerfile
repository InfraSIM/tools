# Use an official Python runtime as a base image
FROM ubuntu:16.04
ENV DEBIAN_FRONTEND noninteractive

# Set the working directory to /app
WORKDIR /infrasim-compute

# Copy the current directory contents into the container at /app
ADD . /infrasim-compute

# Install dependency
RUN apt-get update
RUN apt-get install -y socat build-essential libssl-dev libffi-dev python-dev libaio-dev bridge-utils git apt-utils python-pip
RUN apt-get install -y net-tools libnuma-dev libglib2.0-dev libapt-pkg5.0 iputils-ping isc-dhcp-client
RUN apt-get install -y openssh-server
RUN apt-get install -y vim curl sudo
RUN apt-get install -y --no-install-recommends python-apt
RUN apt-get install -y ca-certificates
RUN apt-get install -y apt-transport-https wget

# Add public bintray to sources.list
RUN echo "deb https://dl.bintray.com/infrasim/deb xenial main" >> /etc/apt/sources.list

# install setuptools
RUN pip install setuptools

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# config SSH service
RUN mkdir /var/run/sshd
# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

# create user
RUN mkdir /home/infrasim
RUN useradd infrasim -g sudo -s /bin/bash
RUN echo 'infrasim:infrasim' | chpasswd
RUN echo 'infrasim ALL=NOPASSWD: ALL' >> /etc/sudoers
RUN chown infrasim /home/infrasim

# Make port 80 available to the world outside this container
EXPOSE 80
EXPOSE 22

# Run app.py when the container launches
RUN ["sudo", "python", "setup.py", "install"]

# RUN which infrasim
USER infrasim
RUN ["sudo", "infrasim", "init", "-f"]

ENTRYPOINT service ssh restart && bash
