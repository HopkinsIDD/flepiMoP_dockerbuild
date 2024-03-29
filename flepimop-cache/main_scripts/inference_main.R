suppressMessages(library(parallel))
suppressMessages(library(foreach))
suppressMessages(library(parallel))
suppressMessages(library(doParallel))
options(readr.num_columns = 0)

option_list = list(
  optparse::make_option(c("-c", "--config"), action="store", default=Sys.getenv("CONFIG_PATH"), type='character', help="path to the config file"),
  optparse::make_option(c("-u","--run_id"), action="store", type='character', help="Unique identifier for this run", default = Sys.getenv("FLEPI_RUN_INDEX",flepicommon::run_id())),
  optparse::make_option(c("-s", "--npi_scenarios"), action="store", default=Sys.getenv("FLEPI_NPI_SCENARIOS", 'all'), type='character', help="name of the intervention scenario to run, or 'all' to run all of them"),
  optparse::make_option(c("-d", "--outcome_scenarios"), action="store", default=Sys.getenv("FLEPI_OUTCOME_SCENARIOS", 'all'), type='character', help="name of the outcome scenario to run, or 'all' to run all of them"),
  optparse::make_option(c("-j", "--jobs"), action="store", default=Sys.getenv("FLEPI_NJOBS", parallel::detectCores()), type='integer', help="Number of jobs to run in parallel"),
  optparse::make_option(c("-k", "--iterations_per_slot"), action="store", default=Sys.getenv("FLEPI_ITERATIONS_PER_SLOT", NA), type='integer', help = "number of iterations to run for this slot"),
  optparse::make_option(c("-n", "--slots"), action="store", default=Sys.getenv("FLEPI_NUM_SLOTS", as.numeric(NA)), type='integer', help = "Number of slots to run."),
  optparse::make_option(c("-b", "--this_block"), action="store", default=Sys.getenv("FLEPI_BLOCK_INDEX",1), type='integer', help = "id of this block"),
  optparse::make_option(c("-t", "--stoch_traj_flag"), action="store", default=Sys.getenv("FLEPI_STOCHASTIC_RUN",FALSE), type='logical', help = "Stochastic SEIR and outcomes trajectories if true"),
  optparse::make_option(c("--ground_truth_start"), action = "store", default = Sys.getenv("GT_START_DATE", ""), type = "character", help = "First date to include groundtruth for"),
  optparse::make_option(c("--ground_truth_end"), action = "store", default = Sys.getenv("GT_END_DATE", ""), type = "character", help = "Last date to include groundtruth for"),
  optparse::make_option(c("-p", "--flepi_path"), action="store", type='character', help="path to the flepiMoP directory", default = Sys.getenv("FLEPI_PATH", "flepiMoP")),
  optparse::make_option(c("-y", "--python"), action="store", default=Sys.getenv("PYTHON_PATH","python3"), type='character', help="path to python executable"),
  optparse::make_option(c("-r", "--rpath"), action="store", default=Sys.getenv("RSCRIPT_PATH","Rscript"), type = 'character', help = "path to R executable"),
  optparse::make_option(c("-R", "--is-resume"), action="store", default=Sys.getenv("RESUME_RUN",FALSE), type = 'logical', help = "Is this run a resume"),
  optparse::make_option(c("-I", "--is-interactive"), action="store", default=Sys.getenv("RUN_INTERACTIVE",Sys.getenv("INTERACTIVE_RUN", FALSE)), type = 'logical', help = "Is this run an interactive run"),
  optparse::make_option(c("-L", "--reset_chimeric_on_accept"), action = "store", default = Sys.getenv("FLEPI_RESET_CHIMERICS", FALSE), type = 'logical', help = 'Should the chimeric parameters get reset to global parameters when a global acceptance occurs')
)

parser=optparse::OptionParser(option_list=option_list)
opt = optparse::parse_args(parser)

print("Starting")
if(opt$config == ""){
  optparse::print_help(parser)
  stop(paste(
    "Please specify a config YAML file with either -c option or CONFIG_PATH environment variable."
  ))
}

print(paste('Running ',opt$j,' jobs in parallel'))

config <- flepicommon::load_config(opt$config)

# Parse scenarios arguments
##If outcome scenarios are specified check their existence
outcome_scenarios <- opt$outcome_scenarios
if(all(outcome_scenarios == "all")) {
  outcome_scenarios<- config$outcomes$scenarios
} else if (!(outcome_scenarios %in% config$outcomes$scenarios)){
  message(paste("Invalid outcome scenario argument:[",paste(setdiff(outcome_scenarios, config$outcome$scenarios)), "]did not match any of the named args in", paste(config$outcomes$scenarios, collapse = ", "), "\n"))
  quit("yes", status=1)
}

##If intervention scenarios are specified check their existence
npi_scenarios <- opt$npi_scenarios
if (all(npi_scenarios == "all")){
  npi_scenarios <- config$interventions$scenarios
} else if (!all(npi_scenarios %in% config$interventions$scenarios)) {
  message(paste("Invalid intervention scenario arguments: [",paste(setdiff(npi_scenarios, config$interventions$scenarios)), "] did not match any of the named args in ", paste(config$interventions$scenarios, collapse = ", "), "\n"))
  quit("yes", status=1)
}

if(is.na(opt$iterations_per_slot)) {
  opt$iterations_per_slot <- config$inference$iterations_per_slot
}

if(is.na(opt$slots)) {
  opt$slots <- config$nslots
}

cl <- parallel::makeCluster(opt$j)
doParallel::registerDoParallel(cl)
print(paste0("Making cluster with ", opt$j, " cores."))

flepicommon::prettyprint_optlist(list(npi_scenarios=npi_scenarios,outcome_scenarios=outcome_scenarios,slots=seq_len(opt$slots)))
foreach(npi_scenario = npi_scenarios) %:%
foreach(outcome_scenario = outcome_scenarios) %:%
foreach(flepi_slot = seq_len(opt$slots)) %dopar% {
  print(paste("Slot", flepi_slot, "of", opt$slots))


  ground_truth_start_text <- NULL
  ground_truth_end_text <- NULL
  if (nchar(opt$ground_truth_start) > 0) {
    ground_truth_start_text <- c("--ground_truth_start", opt$ground_truth_start)
  }
  if (nchar(opt$ground_truth_start) > 0) {
    ground_truth_end_text <- c("--ground_truth_end", opt$ground_truth_end)
  }

  err <- system(
    paste(
      opt$rpath,
      file.path(opt$flepi_path, "flepimop", "main_scripts","inference_slot.R"),
        "-c", opt$config,
        "-u", opt$run_id,
        "-s", opt$npi_scenarios,
        "-d", opt$outcome_scenarios,
        "-j", opt$jobs,
        "-k", opt$iterations_per_slot,
        "-i", flepi_slot,
        "-b", opt$this_block,
        "-t", opt$stoch_traj_flag,
        ground_truth_start_text,
        ground_truth_end_text,
        "-p", opt$flepi_path,
        "-y", opt$python,
        "-r", opt$rpath,
        "-R", opt[["is-resume"]],
        "-I", opt[["is-interactive"]],
        "-L", opt$reset_chimeric_on_accept,
      sep = " ")
    )
  if(err != 0){quit("no")}
}
parallel::stopCluster(cl)
