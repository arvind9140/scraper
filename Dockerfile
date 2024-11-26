# Use the official Python base image
FROM python:3.11.4
 
# Install dependencies, Chrome, and ChromeDriver
RUN apt-get update -qq -y && \
    apt-get install -y \
        libasound2 \
        libatk-bridge2.0-0 \
        libgtk-4-1 \
        libnss3 \
        xdg-utils \
        wget \
        unzip && \
    wget -q -O chrome-linux64.zip https://bit.ly/chrome-linux64-121-0-6167-85 && \
    unzip chrome-linux64.zip && \
    rm chrome-linux64.zip && \
    mv chrome-linux64 /opt/chrome/ && \
    ln -s /opt/chrome/chrome /usr/local/bin/ && \
    wget -q -O chromedriver-linux64.zip https://bit.ly/chromedriver-linux64-121-0-6167-85 && \
    unzip -j chromedriver-linux64.zip chromedriver-linux64/chromedriver && \
    rm chromedriver-linux64.zip && \
    mv chromedriver /usr/local/bin/ && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
 
# Install Python dependencies
RUN pip3 install selenium==4.18.1
 
# Set the working directory
WORKDIR /app
 
# Copy application files
COPY . .
 
RUN pip3 install -r requirements.txt

EXPOSE 8000
 
# Run the Python script as the default command
CMD ["python", "api.py"]