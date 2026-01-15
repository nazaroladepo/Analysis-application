// src/api.js
import axios from 'axios';

// Use environment variable for API base URL, fallback to localhost for development
const API_BASE = process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000/api';

export async function analyzePlant(species, plantId, date, segmentationMethod = "sam3") {
  const url = `${API_BASE}/analyze-plant/${species}/${plantId}?date=${date}&segmentation_method=${segmentationMethod}`;
  const res = await axios.post(url);
  return res.data;
}

export async function getPlantResults(species, plantId, date) {
  const url = `${API_BASE}/plant-results/${species}/${plantId}?date=${date}`;
  const res = await axios.get(url);
  return res.data;
}



export async function getVegetationTimeline(species, plantId, indexType) {
  const url = `${API_BASE}/plant-timeline/${species}/${plantId}/vegetation/${indexType}`;
  const res = await axios.get(url);
  return res.data;
}

export async function getTextureTimeline(species, plantId, bandName, textureType) {
  const url = `${API_BASE}/plant-timeline/${species}/${plantId}/texture/${bandName}/${textureType}`;
  const res = await axios.get(url);
  return res.data;
}

export async function getMorphologyTimeline(species, plantId, feature) {
  const url = `${API_BASE}/plant-timeline/${species}/${plantId}/morphology/${feature}`;
  const res = await axios.get(url);
  return res.data;
}

export async function getDatabaseData(species, plantId, date) {
  const url = `${API_BASE}/plant-database-data/${species}/${plantId}?date=${date}`;
  const res = await axios.get(url);
  return res.data;
}

export async function getAvailablePlants() {
  const url = `${API_BASE}/available-plants`;
  const res = await axios.get(url);
  return res.data;
}

export async function getPlantDates(species, plantId) {
  const url = `${API_BASE}/plant-dates/${species}/${plantId}`;
  const res = await axios.get(url);
  return res.data;
}

/**
 * Upload files to the backend (raw or result).
 * @param {FileList|Array<File>} files - The files to upload.
 * @param {string} endpoint - 'raw-files' or 'result-files'
 * @param {Function} onProgress - Optional progress callback
 * @returns {Promise<Object>} - The response from the backend.
 */
export async function uploadFiles(files, endpoint = "raw-files", segmentationMethod = "sam3") {
  const url = `${API_BASE}/upload/${endpoint}?segmentation_method=${segmentationMethod}`;
  const formData = new FormData();

  // Append each file to the form data
  for (let i = 0; i < files.length; i++) {
    formData.append("files", files[i], files[i].webkitRelativePath || files[i].name);
  }

  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Upload failed");
  }

  return await response.json();
}

export async function getUploadStatus() {
  const url = `${API_BASE}/upload/status`;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Failed to fetch upload status");
  return await response.json();
}

export async function getChartsData(species = null) {
  const url = `${API_BASE}/charts/unified-data`;
  const params = species ? { species } : {};
  const res = await axios.get(url, { params });
  return res.data;
}

export async function getGenotypeMapping() {
  const url = `${API_BASE}/charts/genotype-mapping`;
  const res = await axios.get(url);
  return res.data;
}

export async function getPCA(dimensions = 2, species = null) {
  const url = `${API_BASE}/charts/pca`;
  const params = { dimensions };
  if (species) params.species = species;
  const res = await axios.get(url, { params });
  return res.data;
}

export async function getTSNE(dimensions = 2, species = null) {
  const url = `${API_BASE}/charts/tsne`;
  const params = { dimensions };
  if (species) params.species = species;
  const res = await axios.get(url, { params });
  return res.data;
}

export async function downloadImagesZip(imageUrls, tabName) {
  const url = `${API_BASE}/download-images-zip`;
  const res = await axios.post(url, {
    image_urls: imageUrls,
    tab_name: tabName
  }, {
    responseType: 'blob' // Important: receive as blob for download
  });
  return res.data;
}
