const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Configuration
const baseUrl = process.env.NEXT_PUBLIC_FRONTEND_URL || 'https://mrwhiteaidogbuddy.com/';
const outputPath = path.join(process.cwd(), 'public', 'sitemap.xml');
const pagesDir = path.join(process.cwd(), 'src', 'app');

// Excluded paths
const excludedPaths = [
  '/api/',
  '/_',
  '/auth/',
  '/login',
  '/register',
  '/404',
  '/500',
  '/not-found',
  '/layout',
  '/page',
];

// Priority mapping
const priorityMap = {
  '/': 1.0,
  '/about': 0.8,
  '/subscription': 0.8,
  '/product': 0.8,
  '/questbook': 0.8,
  '/hub': 0.8,
  '/contact': 0.7,
};

// Function to get all pages
function getPages() {
  // Get all page.tsx files
  const pageFiles = glob.sync(`${pagesDir}/**/page.tsx`);

  // Extract routes from file paths
  return pageFiles
    .map(file => {
      // Remove base directory and page.tsx
      let route = file
        .replace(pagesDir, '')
        .replace(/\/page\.tsx$/, '')
        .replace(/\(.*?\)\//g, ''); // Remove route groups like (user)

      // Handle root route
      if (!route) route = '/';
      else route = `${route}`;

      return route;
    })
    .filter(route => {
      // Filter out excluded paths
      return !excludedPaths.some(excluded => route.includes(excluded));
    });
}

// Generate sitemap XML
function generateSitemap(pages) {
  const today = new Date().toISOString();

  let sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n';
  sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n';

  pages.forEach(page => {
    const priority = priorityMap[page] || 0.5;

    sitemap += '  <url>\n';
    sitemap += `    <loc>${baseUrl}${page}</loc>\n`;
    sitemap += `    <lastmod>${today}</lastmod>\n`;
    sitemap += '    <changefreq>weekly</changefreq>\n';
    sitemap += `    <priority>${priority}</priority>\n`;
    sitemap += '  </url>\n';
  });

  sitemap += '</urlset>';
  return sitemap;
}

// Main function
function main() {
  try {
    const pages = getPages();
    const sitemap = generateSitemap(pages);

    fs.writeFileSync(outputPath, sitemap);
    console.log(`Sitemap generated at ${outputPath}`);
  } catch (error) {
    console.error('Error generating sitemap:', error);
  }
}

main(); 