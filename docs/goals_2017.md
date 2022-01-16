# Goal 1:
Create one or more maps using the Dam data for an interactive web page.  

Decisions:
1. Mapfile will be KML for use in Google Map / Google Earth, with layers including
   1. Dam points
   1. Streamflow
   1. DEM
   1. Satellite imagery
   1. State boundaries
   1. County boundaries
1. The map extent will be the Continental US (so you can zoom out to see the relative location with state and county boundaries)
1. Dam points layer 
   1. Will contain clickable URLs in the properties for each dam
   1. URLs will open to photos in Google Drive files 
   1. Will contain a date, either photo date (newer photos) or dam construction date (matched by hand)
   1. Dam points in the KML will be displayed as a symbol, colored by the date

Options for the interactive map:
1. Could display 2 linked maps from the same map file, with different layers in each window, that pan and zoom in tandem
2. Layers could be turned on/off by the user or the programmer in each window


# Goal 2:
Create a map that can be printed at 150 dpi

Decisions:
1. Decide on what to have visible on print version



Questions:
1. Was there a reason to create a convex hull around the points?  Possibly for 
   identifying photos that are the same dam location.
