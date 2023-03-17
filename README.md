# flepiMoP_dockerbuild

## Scope
The purpose of this repo is to build a docker image which contains R environment and other files for flepiMoP(`Flexible Epidemic Modeling Pipeline` by the Johns Hopkins University Infectious Disease Dynamics COVID-19 Working Group) development/deployment. The main flepiMoP repo is [here](https://github.com/HopkinsIDD/flepiMoP)

## Usage
This repo should be used in the following scenarios, in this order:

### git clone
If the repo does not exist in your computer, clone it using the command:
```shell
git clone https://github.com/HopkinsIDD/flepiMoP_dockerbuild.git
```

### Builind a docker image for flepiMoP development/deployment
Pre-requisites: 
1. If the repo does not exist on your computer, clone it as shown in the previous section
2. Make sure that Docker Desktop is installed on your computer, then activate it
3. (optional) Create a repository on the Docker hub as explained [here](https://docs.docker.com/docker-hub/repos/)

To build an image:
1. `cd flepiMoP_dockerbuild` to move to "build context" dir,
2. `docker build -t flepimop .` to build a image.
3. (optional) `docker push <hub-user>/<repo-name>:flepimop` to push the image to the Docker hub

**Note that the container build supports amd64 CPU architecture only, other architectures are unconfirmed. In using M1 MAC etc., please use the build kit to build an image with specifying the platform/architecture such as:
```shell
docker buildx build --platform=linux/amd64 -t .
```

## License

This project is licensed under GPL v3.0.
If you would like to see the detailed LICENSE click [here](LICENSE).


## More Information

More information can be found in these files:
* [LICENSE](LICENSE)
* [flepiMoP(Flexible Epidemic Modeling Pipeline, by the Johns Hopkins University Infectious Disease Dynamics COVID-19 Working Group)](https://github.com/HopkinsIDD/flepiMoP)
* [Docker Curriculum](https://docker-curriculum.com/)

## Notes
If you have any questions or issues you can create a new [issue here][issues].

[issues]: https://github.com/HopkinsIDD/flepiMoP_dockerbuild/issues/new
