# Build stage
FROM node:24-alpine as build-stage

# Set working directory
WORKDIR /app

# Copy package.json and install dependencies
COPY package*.json ./
RUN npm install

# Copy source code and build the application
COPY . .
RUN npm run build

# Production stage
FROM nginx:stable-alpine

# Copy built assets from build-stage to Nginx serve directory
COPY --from=build-stage /app/dist /usr/share/nginx/html
# Note: Use /app/build instead of /app/dist if you are using Create React App

# Expose port 80 for Nginx
EXPOSE 80

# Start Nginx server
CMD ["nginx", "-g", "daemon off;"]