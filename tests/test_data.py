"""
Runs tests on some fetched data from the web.

This will ensure that all particle fields are populated correctly, and that they can
be read in.
"""

from tests.helper import requires
from swiftsimio import load, mask

import h5py

from unyt import unyt_array as array
from unyt import K
from numpy import logical_and, isclose
from numpy import array as numpy_array


@requires("cosmological_volume.hdf5")
def test_cosmology_metadata(filename):
    """
    Tests to see if we get the unpacked cosmology metadata correct.
    """

    data = load(filename)

    assert data.metadata.a == data.metadata.scale_factor

    assert data.metadata.a == 1.0 / (1.0 + data.metadata.redshift)

    return


@requires("cosmological_volume.hdf5")
def test_time_metadata(filename):
    """
    This tests the time metadata and also tests the ability to include two items at once from
    the same header attribute.
    """

    data = load(filename)

    assert data.metadata.z == data.metadata.redshift

    assert data.metadata.t == data.metadata.time

    return


@requires("cosmological_volume.hdf5")
def test_temperature_units(filename):
    """
    This tests checks if we correctly read in temperature units. Based on a past bug, to make
    sure we never break this again.
    """

    data = load(filename)
    data.gas.temperatures.convert_to_units(K)

    return


@requires("cosmological_volume.hdf5")
def test_units(filename):
    """
    Tests that these fields have the same units within SWIFTsimIO as they
    do in the SWIFT code itself.
    """

    data = load(filename)

    shared = ["coordinates", "masses", "particle_ids", "velocities"]

    baryon = [
        "maximal_temperatures",
        "maximal_temperature_scale_factors",
        "iron_mass_fractions_from_snia",
        "metal_mass_fractions_from_agb",
        "metal_mass_fractions_from_snii",
        "metal_mass_fractions_from_snia",
        "smoothed_element_mass_fractions",
        "smoothed_iron_mass_fractions_from_snia",
        "smoothed_metal_mass_fractions",
    ]

    to_test = {
        "gas": [
            "densities",
            "entropies",
            "internal_energies",
            "smoothing_lengths",
            "pressures",
            "temperatures",
        ]
        + baryon
        + shared,
        "dark_matter": shared,
    }

    for ptype, properties in to_test.items():
        field = getattr(data, ptype)

        # Now need to extract the particle paths in the original hdf5 file
        # for comparison...
        paths = numpy_array(field.particle_metadata.field_paths)
        names = numpy_array(field.particle_metadata.field_names)

        for property in properties:
            # Read the 0th element, and compare in CGS units.
            our_units = getattr(field, property)[0]

            our_units.convert_to_cgs()

            # Find the path in the HDF5 for our linked dataset
            path = paths[names == property][0]

            with h5py.File(filename, "r") as handle:
                swift_units = handle[path].attrs[
                    "Conversion factor to CGS (not including cosmological corrections)"
                ][0]
                swift_units *= handle[path][0]

            assert isclose(swift_units, our_units.value).all()

    # If we didn't crash out, we gucci.
    return


@requires("cosmological_volume.hdf5")
def test_reading_select_region_metadata(filename):
    """
    Tests reading select regions of the volume.
    """

    full_data = load(filename)

    # Mask off the centre of the volume.
    mask_region = mask(filename, spatial_only=True)

    restrict = array(
        [full_data.metadata.boxsize * 0.26, full_data.metadata.boxsize * 0.74]
    ).T

    mask_region.constrain_spatial(restrict=restrict)

    selected_data = load(filename, mask=mask_region)

    selected_coordinates = selected_data.gas.coordinates

    # Now need to repeat teh selection by hand:
    subset_mask = logical_and.reduce(
        [
            logical_and(x > y_lower, x < y_upper)
            for x, (y_lower, y_upper) in zip(full_data.gas.coordinates.T, restrict)
        ]
    )

    # We also need to repeat for the thing we just selected; the cells only give
    # us an _approximate_ selection!
    selected_subset_mask = logical_and.reduce(
        [
            logical_and(x > y_lower, x < y_upper)
            for x, (y_lower, y_upper) in zip(selected_data.gas.coordinates.T, restrict)
        ]
    )

    hand_selected_coordinates = full_data.gas.coordinates[subset_mask]

    assert (
        hand_selected_coordinates == selected_coordinates[selected_subset_mask]
    ).all()
    return


@requires("cosmological_volume.hdf5")
def test_reading_select_region_metadata_not_spatial_only(filename):
    """
    The same as test_reading_select_region_metadata but for spatial_only=False.
    """

    full_data = load(filename)

    # Mask off the centre of the volume.
    mask_region = mask(filename, spatial_only=False)

    restrict = array(
        [full_data.metadata.boxsize * 0.26, full_data.metadata.boxsize * 0.74]
    ).T

    mask_region.constrain_spatial(restrict=restrict)

    selected_data = load(filename, mask=mask_region)

    selected_coordinates = selected_data.gas.coordinates

    # Now need to repeat the selection by hand:
    subset_mask = logical_and.reduce(
        [
            logical_and(x > y_lower, x < y_upper)
            for x, (y_lower, y_upper) in zip(full_data.gas.coordinates.T, restrict)
        ]
    )

    # We also need to repeat for the thing we just selected; the cells only give
    # us an _approximate_ selection!
    selected_subset_mask = logical_and.reduce(
        [
            logical_and(x > y_lower, x < y_upper)
            for x, (y_lower, y_upper) in zip(selected_data.gas.coordinates.T, restrict)
        ]
    )

    hand_selected_coordinates = full_data.gas.coordinates[subset_mask]

    assert (
        hand_selected_coordinates == selected_coordinates[selected_subset_mask]
    ).all()

    return
