# -*- coding: utf-8 -*-
"""
Parametric quarter model of a finite-width plate with a central hole under
uniaxial tension, built with the Abaqus/CAE scripting interface.

Geometry (quarter model, symmetry on x = 0 and y = 0):
    width W along x, length L along y, hole diameter d at the origin.
    Tension sigma (gross section) is applied on the top edge y = L/2.
    The peak stress S22 is at the hole edge, point (d/2, 0).

Works with Abaqus 2024+ (Python 3) and older releases (Python 2.7).
"""
from __future__ import print_function

import math

from abaqus import mdb
from abaqusConstants import (TWO_D_PLANAR, DEFORMABLE_BODY, CLOCKWISE, ON, OFF,
                             FINER, QUAD_DOMINATED, FREE, STANDARD,
                             CPS8R, CPS6M, ELEMENT_NODAL)
import mesh


def build_model(name, W, L, t, d, E, nu, sigma, arc_elements, global_size):
    """Create the model `name` and return it. Units: mm, N, MPa."""
    r = d / 2.0
    model = mdb.Model(name=name)

    # Sketch of the quarter plate: bottom edge, right edge, top edge,
    # left edge, then the quarter hole arc.
    s = model.ConstrainedSketch(name='profile', sheetSize=2.0 * L)
    s.Line(point1=(r, 0.0), point2=(W / 2.0, 0.0))
    s.Line(point1=(W / 2.0, 0.0), point2=(W / 2.0, L / 2.0))
    s.Line(point1=(W / 2.0, L / 2.0), point2=(0.0, L / 2.0))
    s.Line(point1=(0.0, L / 2.0), point2=(0.0, r))
    s.ArcByCenterEnds(center=(0.0, 0.0), point1=(0.0, r), point2=(r, 0.0),
                      direction=CLOCKWISE)

    p = model.Part(name='Plate', dimensionality=TWO_D_PLANAR,
                   type=DEFORMABLE_BODY)
    p.BaseShell(sketch=s)

    # Edges and vertices picked by a point that lies on each of them
    c45 = math.cos(math.radians(45.0))
    arc = p.edges.findAt(((r * c45, r * c45, 0.0),))
    bottom = p.edges.findAt((((r + W / 2.0) / 2.0, 0.0, 0.0),))
    left = p.edges.findAt(((0.0, (r + L / 2.0) / 2.0, 0.0),))
    top = p.edges.findAt(((W / 4.0, L / 2.0, 0.0),))

    p.Set(faces=p.faces[:], name='All')
    p.Set(edges=bottom, name='Bottom')
    p.Set(edges=left, name='Left')
    p.Set(vertices=p.vertices.findAt(((r, 0.0, 0.0),)), name='HolePt')
    p.Surface(side1Edges=top, name='Top')

    # Material and plane-stress section
    mat = model.Material(name='Steel')
    mat.Elastic(table=((E, nu),))
    model.HomogeneousSolidSection(name='PlateSection', material='Steel',
                                  thickness=t)
    p.SectionAssignment(region=p.sets['All'], sectionName='PlateSection')

    # Mesh: global size, refined arc, 8-node plane-stress quads
    p.seedPart(size=global_size, deviationFactor=0.1, minSizeFactor=0.1)
    p.seedEdgeByNumber(edges=arc, number=arc_elements, constraint=FINER)
    p.setMeshControls(regions=p.faces[:], elemShape=QUAD_DOMINATED,
                      technique=FREE)
    p.setElementType(regions=(p.faces[:],), elemTypes=(
        mesh.ElemType(elemCode=CPS8R, elemLibrary=STANDARD),
        mesh.ElemType(elemCode=CPS6M, elemLibrary=STANDARD)))
    p.generateMesh()

    # Assembly, step, boundary conditions and load
    a = model.rootAssembly
    inst = a.Instance(name='Plate-1', part=p, dependent=ON)
    model.StaticStep(name='Load', previous='Initial')
    model.XsymmBC(name='SymX', createStepName='Initial',
                  region=inst.sets['Left'])
    model.YsymmBC(name='SymY', createStepName='Initial',
                  region=inst.sets['Bottom'])
    # Negative pressure = tension
    model.Pressure(name='Tension', createStepName='Load',
                   region=inst.surfaces['Top'], magnitude=-sigma)
    return model


def run_job(model_name, job_name):
    """Write the input file, run the analysis and wait for it to finish."""
    job = mdb.Job(name=job_name, model=model_name, numCpus=1)
    job.writeInput(consistencyChecking=OFF)
    job.submit(consistencyChecking=OFF)
    job.waitForCompletion()
    return job_name + '.odb'


def peak_stress(odb_path):
    """Return (S22 at the hole edge node, number of elements)."""
    from odbAccess import openOdb
    odb = openOdb(path=odb_path, readOnly=True)
    try:
        inst = odb.rootAssembly.instances['PLATE-1']
        frame = odb.steps['Load'].frames[-1]
        stress = frame.fieldOutputs['S']
        sub = stress.getSubset(region=inst.nodeSets['HOLEPT'],
                               position=ELEMENT_NODAL)
        # One value per element sharing the node: average them
        values = [v.data[1] for v in sub.values]
        s22 = sum(values) / len(values)
        n_elem = len(inst.elements)
    finally:
        odb.close()
    return s22, n_elem
