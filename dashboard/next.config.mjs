// Static export: the dashboard is plain files served offline; all data comes from the cloud API at runtime.
/** @type {import('next').NextConfig} */
export default { output: "export", images: { unoptimized: true }, trailingSlash: true };
