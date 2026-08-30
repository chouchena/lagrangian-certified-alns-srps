# Test Benchmark Instances for the Orienteering Problem with Synchronization

**Jorge Riera-Ledesma**, **Juan-José Salazar-González**  
*Selective Routing Problem with Synchronization*,  
Computers & Operations Research, Volume 135, 2021, Article 105465,  
ISSN 0305-0548,  
[https://doi.org/10.1016/j.cor.2021.105465](https://doi.org/10.1016/j.cor.2021.105465)

---

## Description

This repository contains the generated instances themselves, together with the visual representation of the obtained solutions and their corresponding objective values.

### Repository Structure

- **`input/`**  
  Includes the generated input instances in **JSON** format, organized into separate instance families.  
  Each family is structured into two subdirectories:
  - **`targets/`** — contains the spatial coordinates of the targets along with their respective processing times.  
  - **`instances/`** — contains the additional input parameters associated with each target and scenario configuration.

- **`output/`**  
  Stores the solutions obtained by the proposed algorithm, including their objective values and, when applicable, their graphical representations.

---

## Citation

If you use any of the instances, generation tools, or solution data contained in this repository, please cite the following publication:

> J. Riera-Ledesma, J.-J. Salazar-González,  
> *Selective Routing Problem with Synchronization*,  
> *Computers & Operations Research*, Vol. 135, 2021, Article 105465.  
> DOI: [10.1016/j.cor.2021.105465](https://doi.org/10.1016/j.cor.2021.105465)

---

## Acknowledgments 

The authors gratefully acknowledge the use of the instance generation and evaluation framework developed within the context of this research for reproducibility and benchmarking purposes.
