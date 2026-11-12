FROM node:20-alpine

WORKDIR /app

# Pehle package files copy karke dependencies install karein
COPY package*.json ./
RUN npm install

# Baaki frontend code copy karein
COPY . .

# Vite ka default port expose karein
EXPOSE 5173

# --host 0.0.0.0 lagana zaroori hai taaki Docker container ke bahar browser mein UI khule
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]