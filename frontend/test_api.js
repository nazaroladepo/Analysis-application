// Test script for the frontend API functions
import { getAvailablePlants } from './src/api.js';

async function testFrontendAPI() {
    try {
        console.log('Testing getAvailablePlants API function...');

        const data = await getAvailablePlants();

        console.log('✅ API function working!');
        console.log('Available species:', data.species);
        console.log('Plants by species:', data.plants_by_species);

        // Test with a specific species
        if (data.species && data.species.length > 0) {
            const testSpecies = data.species[0];
            console.log(`\nTesting with species: ${testSpecies}`);
            console.log('Plants:', data.plants_by_species[testSpecies]);
        }

    } catch (error) {
        console.error('❌ Error testing frontend API:', error);
    }
}

// Run the test
testFrontendAPI(); 