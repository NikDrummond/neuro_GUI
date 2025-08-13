"""3D rendering functionality for neuron visualization using VTK and vedo."""

import logging
import numpy as np
import vedo as vd
import Neurosetta as nr
from typing import Optional, Any, Tuple
from config import RENDERING_CONSTANTS


class NeuronRenderer:
    """Handles 3D rendering of neuron data using vedo/VTK."""
    
    def __init__(self, plotter: vd.Plotter):
        """Initialize the renderer.
        
        Args:
            plotter: vedo Plotter instance for rendering
        """
        self.plotter = plotter
        self.current_object = None
        self.current_lines = None
        self.soma = None
        self.neuron_color = RENDERING_CONSTANTS['DEFAULT_NEURON_COLOR']
        self.current_mesh = None
        
        # Set up camera for parallel projection
        cam = self.plotter.renderer.GetActiveCamera()
        cam.SetParallelProjection(True)
    
    def render_point_cloud(self, coordinates: np.ndarray) -> None:
        """Render a point cloud from coordinate data.
        
        Args:
            coordinates: Array of 3D coordinates
        """
        points = vd.Points(
            coordinates, 
            r=RENDERING_CONSTANTS['POINT_RADIUS'], 
            c=RENDERING_CONSTANTS['POINT_CLOUD_COLOR']
        )
        self._display(points)
        logging.info(f"Rendered point cloud with {len(coordinates)} points")
    
    def render_neuron(self, neuron: Any) -> None:
        """Render a neuron object with lines and soma.
        
        Args:
            neuron: Neurosetta neuron object
        """
        # Create neuron lines
        lines = nr.plotting._vd_tree_lines(neuron, c=self.neuron_color)
        
        # Create soma marker
        root_coords = nr.g_vert_coords(neuron, nr.g_root_ind(neuron))[0]
        soma = vd.Point(
            root_coords, 
            c=RENDERING_CONSTANTS['SOMA_COLOR'], 
            r=RENDERING_CONSTANTS['SOMA_RADIUS']
        )
        
        # Store references
        self.current_lines = lines
        self.soma = soma
        
        # Display as assembly
        assembly = vd.Assembly([lines, soma])
        self._display(assembly)
        
        logging.info("Rendered neuron with lines and soma")
    
    def render_subtree(self, neuron: Any) -> None:
        """Render only the subtree under the current neuron root.
        
        Args:
            neuron: Neurosetta neuron object
        """
        if not neuron:
            logging.warning("Cannot render subtree: neuron is None")
            return
        
        # Get subtree visualization from Neurosetta
        subtree_result = nr.plotting._vd_subtree_lns(neuron)
        
        # Normalize to list of actors
        if isinstance(subtree_result, (tuple, list)):
            actors = list(subtree_result)
        else:
            actors = [subtree_result]
        
        # soma
        root_coords = nr.g_vert_coords(neuron, nr.g_root_ind(neuron))[0]
        soma = vd.Point(
            root_coords, 
            c=RENDERING_CONSTANTS['SOMA_COLOR'], 
            r=RENDERING_CONSTANTS['SOMA_RADIUS']
        )
        self.soma = soma
        actors.append(soma)
        # Display subtree
        assembly = vd.Assembly(actors)
        self._display(assembly)
        
        logging.info("Rendered neuron subtree")
    
    def set_neuron_color(self, color: str) -> None:
        """Set the color of the neuron visualization.
        
        Args:
            color: Color name or hex string
        """
        self.neuron_color = color
        
        # Update current visualization if present
        if self.current_lines:
            self.current_lines.c(color)
        if self.soma:
            self.soma.c(color)
        
        self.plotter.render()
        logging.info(f"Set neuron color to: {color}")
    
    def clear(self) -> None:
        """Clear the current visualization."""
        self.plotter.clear()
        self.current_object = None
        self.current_lines = None
        self.soma = None
    
    def _display(self, obj: Any) -> None:
        """Display an object in the plotter.
        
        Args:
            obj: vedo object to display
        """
        self.current_object = obj
        self.plotter.clear()
        self.plotter.add(obj)
        self.plotter.show(resetcam=True)
    
    def get_current_object(self) -> Optional[Any]:
        """Get the currently displayed object.
        
        Returns:
            Current vedo object or None
        """
        return self.current_object
    
    def has_neuron_lines(self) -> bool:
        """Check if neuron lines are currently displayed.
        
        Returns:
            True if neuron lines are present
        """
        return self.current_lines is not None
    
    def update_display(self) -> None:
        """Update the display without clearing."""
        self.plotter.render()
    
    def add_mesh(self, mesh) -> None:
        """Add a mesh to the current display.
        
        Args:
            mesh: vedo mesh object to add
        """
        try:
            # Remove existing mesh if present
            if self.current_mesh:
                self.remove_mesh(self.current_mesh)
            
            # Add new mesh to plotter
            self.plotter.add(mesh)
            self.current_mesh = mesh
            self.plotter.render()
            
            logging.info("Added mesh to display")
        except Exception as e:
            logging.error(f"Failed to add mesh: {e}")
    
    def remove_mesh(self, mesh) -> None:
        """Remove a mesh from the display.
        
        Args:
            mesh: vedo mesh object to remove
        """
        try:
            if mesh:
                self.plotter.remove(mesh)
                if self.current_mesh == mesh:
                    self.current_mesh = None
                self.plotter.render()
                
                logging.info("Removed mesh from display")
        except Exception as e:
            logging.error(f"Failed to remove mesh: {e}")
