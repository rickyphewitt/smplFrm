const IMAGE_ID_ATTR = "image-id";
const OPACITY_INCREMENT = 0.1;
const OPACITY_MAX = 1.0;
const CLOCK_REFRESH_MS = 1000;
const SPOTIFY_REFRESH_MS = 5000;

const imageContainer = document.getElementById("image-container");
const progressBar = document.getElementById("progress-bar");
const config = window.SMPL_CONFIG;

function getWindowDimensions() {
    return {
        width: window.innerWidth,
        height: window.innerHeight
    };
}

function buildApiUrl(endpoint) {
    return `${config.host}:${config.port}/api/v1/${endpoint}`;
}

function startProgress() {
    let width = 100;
    const interval = setInterval(() => {
        width -= 1;
        if (width <= 0) {
            clearInterval(interval);
            width = 0;
        }
        progressBar.style.width = `${width}%`;
    }, config.refreshInterval / 100);
}

async function getNextImage() {
    const { width, height } = getWindowDimensions();
    const response = await fetch(buildApiUrl(`images/next?width=${width}&height=${height}`));
    return response.json();
}

async function displayMetadata(imageId) {
    if (!config.displayDate) return;

    try {
        const response = await fetch(buildApiUrl(`images_metadata?image__external_id=${imageId}`));
        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.statusText}`);
        }
        
        const data = await response.json();
        const takenDate = Date.parse(data[0].taken);
        
        if (isNaN(takenDate)) {
            document.getElementById("photo-date").innerHTML = `📷`;
        } else {
            const prettyDate = new Intl.DateTimeFormat("en-US", {
                year: "numeric",
                month: "long"
            }).format(takenDate);
            document.getElementById("photo-date").innerHTML = `📷 ${prettyDate}`;
        }
    } catch (error) {
        console.error('Fetch error:', error);
        document.getElementById("photo-date").innerHTML = `📷`;
    }
}

async function buildImage() {
    const nextImage = await getNextImage();
    const { width, height } = getWindowDimensions();
    const img = new Image();
    img.src = buildApiUrl(`images/${nextImage.id}/display?width=${width}&height=${height}`);
    img.setAttribute(IMAGE_ID_ATTR, nextImage.id);
    return img;
}

function fadeInImage(image, onComplete) {
    let opacity = 0;
    const interval = setInterval(() => {
        opacity += OPACITY_INCREMENT;
        if (opacity >= OPACITY_MAX) {
            clearInterval(interval);
            opacity = OPACITY_MAX;
            if (onComplete) onComplete();
        }
        image.style.opacity = opacity;
    }, config.transitionInterval / 100);
}

async function loadNext(currentImage) {
    const newImage = await buildImage();
    newImage.classList.add("main-img");
    
    newImage.onload = () => {
        imageContainer.appendChild(newImage);
        
        setTimeout(() => {
            fadeInImage(newImage, () => {
                imageContainer.removeChild(currentImage);
            });
            displayMetadata(newImage.getAttribute(IMAGE_ID_ATTR));
            startProgress();
            loadNext(newImage);
        }, config.refreshInterval);
    };
}

async function startImages() {
    const newImage = await buildImage();
    newImage.onload = () => {
        newImage.classList.add("main-img");
        imageContainer.appendChild(newImage);
        
        fadeInImage(newImage);
        displayMetadata(newImage.getAttribute(IMAGE_ID_ATTR));
        startProgress();
        loadNext(newImage);
    };
}

function displayClock() {
    const now = new Date();
    
    // Display current date
    const currentDate = new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric"
    }).format(now);
    document.getElementById("current-date").innerHTML = `📅 ${currentDate}`;
    
    // Display current time without seconds
    const timeString = now.toLocaleTimeString('en-US', { 
        hour: 'numeric', 
        minute: '2-digit',
        hour12: true 
    });
    document.getElementById("current-time").innerHTML = `🕐 ${timeString}`;
    
    setTimeout(displayClock, CLOCK_REFRESH_MS);
}

function displayWeather() {
    if (config.weatherCurrentTemp) {
        document.getElementById("weather-temp").innerHTML = `🌡️ ${config.weatherCurrentTemp}`;
    }
}

function updateSpotifyDisplay(content) {
    const spotifyDiv = document.getElementById("spotify-now-playing");
    spotifyDiv.innerHTML = content;
}

async function getNowPlaying() {
    try {
        const response = await fetch(buildApiUrl('plugins/spotify/now_playing'));
        
        if (!response.ok) {
            const authResponse = await fetch(buildApiUrl('plugins/spotify/auth'));
            if (!authResponse.ok) {
                updateSpotifyDisplay(`<i class="iconoir-spotify spotify-icon"></i>`);
                return;
            }
            
            const authData = await authResponse.json();
            updateSpotifyDisplay(`<a href="${authData.auth_url}"><i class="iconoir-spotify spotify-icon"></i></a>`);
            return;
        }
        
        const data = await response.json();
        updateSpotifyDisplay(`<i class="iconoir-spotify spotify-icon"></i> ${data.artist} - ${data.song}`);
    } catch (error) {
        console.error('Spotify error:', error);
        updateSpotifyDisplay(`<i class="iconoir-spotify spotify-icon"></i>`);
    }
}

function refreshSpotify() {
    const spotifyBar = document.getElementById("spotify-bar");
    spotifyBar.style.display = 'flex';
    
    getNowPlaying();
    setTimeout(refreshSpotify, SPOTIFY_REFRESH_MS);
}

startImages();

if (config.displayClock) {
    window.onload = displayClock;
}

displayWeather();

if (config.pluginSpotifyEnabled) {
    refreshSpotify();
}
