package edu.cmu.ml.rtw.users.matt.randomwalks;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.conf.Configured;
import org.apache.hadoop.filecache.DistributedCache;
import org.apache.hadoop.fs.FSDataInputStream;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.ArrayWritable;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.MapWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.compress.GzipCodec;
import org.apache.hadoop.mapred.FileInputFormat;
import org.apache.hadoop.mapred.FileOutputFormat;
import org.apache.hadoop.mapred.JobClient;
import org.apache.hadoop.mapred.JobConf;
import org.apache.hadoop.mapred.MapReduceBase;
import org.apache.hadoop.mapred.Mapper;
import org.apache.hadoop.mapred.OutputCollector;
import org.apache.hadoop.mapred.Reducer;
import org.apache.hadoop.mapred.Reporter;
import org.apache.hadoop.mapred.SequenceFileOutputFormat;
import org.apache.hadoop.mapred.SequenceFileInputFormat;
import org.apache.hadoop.mapred.TextOutputFormat;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;
import org.apache.log4j.Logger;
import org.apache.mahout.common.IntPairWritable;

import edu.cmu.ml.rtw.util.Pair;

/**
 * Takes the walk file generated by GraphChiWalk and produces a matrix of (node pair) X
 * (path feature).
 */
public class WalkAnalyzer extends Configured implements Tool {
    private final static Logger log = Logger.getLogger(WalkAnalyzer.class);

    public static enum COUNTERS {
        WALK_IDS_SEEN,
        TOO_MANY_HOPS,
        HOP_1,
        HOP_2,
        HOP_3,
        HOP_4,
        HOP_5,
        HOP_6,
        HOP_7,
        HOP_8,
        HOP_9,
        HOP_10,
        HOP_11,
        HOP_12,
        HOP_13,
        HOP_14,
        HOP_15,
        MORE_THAN_15_HOPS,
        RELATION_FOUND,
        NO_RELATION_FOUND,
        NODE_NAME_FOUND,
        NO_NODE_NAME_FOUND,
        NODE_PAIR,
        NOT_ENOUGH_WALKS,
        NO_KEPT_PATHS
    };

    public static class WalkFileMapper extends MapReduceBase implements
            Mapper<IntWritable, IntPairWritable, IntWritable, IntPairWritable> {

        @Override
        public void map(IntWritable key, IntPairWritable value,
                OutputCollector<IntWritable, IntPairWritable> output,
                Reporter reporter) throws IOException {
            output.collect(key, value);
        }
    }

    public static class WalkIdReducer extends MapReduceBase implements
            Reducer<IntWritable, IntPairWritable, IntWritable, IntPairArrayWritable> {

        @Override
        public void reduce(IntWritable walk_id, Iterator<IntPairWritable> values,
                OutputCollector<IntWritable, IntPairArrayWritable> output, Reporter reporter)
                throws IOException {
            reporter.getCounter(COUNTERS.WALK_IDS_SEEN).increment(1);
            ArrayList<IntPairWritable> value_array = new ArrayList<IntPairWritable>();
            int count = 0;
            IntPairWritable iter = null;
            while (values.hasNext()) {
                count++;
                if (count > 100) {
                    // Something is wrong here if there are more than 100 steps for a single walk -
                    // abort.  We could probably set this quite a bit lower (like, 10, or whatever
                    // the maxHops parameter was set to previously, but this will at least catch
                    // pathological cases, which is the main point).
                    reporter.getCounter(COUNTERS.TOO_MANY_HOPS).increment(1);
                    log.warn("Found a walk id with " + count + " hops - skipping it");
                    return;
                }
                iter = values.next();
                IntPairWritable pair = new IntPairWritable();
                pair.set(iter.getFirst(), iter.getSecond());
                value_array.add(pair);
            }
            output.collect(walk_id, IntPairArrayWritable.fromArrayList(value_array));
        }
    }

    public static class NodePairMapper extends MapReduceBase implements
            Mapper<IntWritable, IntPairArrayWritable, IntPairWritable, Text> {

        IntPairWritable out_key = new IntPairWritable();
        Text out_value = new Text();
        Map<Integer, String> node_names = new HashMap<Integer, String>();
        // TODO: this should map to Set<String>, because there could be more than one relation
        // between nodes; need to change the logic below a little bit to handle this, though.
        Map<Long, String> rel_names = new HashMap<Long, String>();

        @Override
        public void configure(JobConf job) {
            Path[] local_files;
            try {
                local_files = DistributedCache.getLocalCacheFiles(job);
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
            try {
                // Node names file is first
                String filename = local_files[0].toString();
                BufferedReader reader = new BufferedReader(new FileReader(filename));
                String line;
                while ((line = reader.readLine()) != null) {
                    String[] parts = line.split("\t");
                    node_names.put(Integer.parseInt(parts[0]), new String(parts[1]));
                }
                reader.close();
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
            // Now the relation file
            try {
                String filename = local_files[1].toString();
                BufferedReader reader = new BufferedReader(new FileReader(filename));
                String line;
                while ((line = reader.readLine()) != null) {
                    String[] parts = line.split("\t");
                    int start_node = Integer.parseInt(parts[0]);
                    int end_node = Integer.parseInt(parts[1]);
                    rel_names.put(intPairToLong(start_node, end_node), new String(parts[2]));
                    rel_names.put(intPairToLong(end_node, start_node), new String(parts[2]+"_inv"));
                }
                reader.close();
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }

        @Override
        public void map(IntWritable key, IntPairArrayWritable value,
                OutputCollector<IntPairWritable, Text> output,
                Reporter reporter) throws IOException {
            ArrayList<IntPairWritable> values = value.toArrayList();
            reporter.getCounter(getHopCounter(values.size())).increment(1);
            Collections.sort(values);
            for (int i=0; i<values.size(); i++) {
                int start_node = values.get(i).getSecond();
                // Beginning vertex - don't output a path feature, but instead a "started from here"
                // feature that keeps track of how many walks I have from this node.  I'm not sure
                // this is really useful, now that I output a total per (source, path) pair...
                out_key.set(start_node, start_node);
                out_value.set("BEGIN");
                output.collect(out_key, out_value);
                WalkPath path = new WalkPath();
                boolean remove_cycles = true;
                boolean lexicalize_paths = false;
                int MAX_PATH_LENGTH = 6;
                int prev_node = start_node;
                for (int j=i+1; j<values.size(); j++) {
                    int hop = values.get(j).getFirst();
                    int node = values.get(j).getSecond();
                    if (j - i > MAX_PATH_LENGTH) break;
                    // We don't need to worry about inverse relations here, because we took care of
                    // that when we created rel_names.
                    String relation = rel_names.get(intPairToLong(prev_node, node));
                    if (relation == null) {
                        reporter.getCounter(COUNTERS.NO_RELATION_FOUND).increment(1);
                        relation = "UNKNOWN_RELATION";
                    } else {
                        reporter.getCounter(COUNTERS.RELATION_FOUND).increment(1);
                    }
                    path.addRelation(relation);
                    // TODO: add a mechanism to filter paths
                    out_key.set(start_node, node);
                    out_value.set(path.getPathString(remove_cycles, lexicalize_paths));
                    output.collect(out_key, out_value);
                    String node_name = Integer.toString(node);
                    /* This is too expensive, I think, and if you're not lexicalizing the nodes
                     * anyway, there's no point in doing this lookup.
                    String node_name = node_names.get(node);
                    if (node_name == null) {
                        reporter.getCounter(COUNTERS.NO_NODE_NAME_FOUND).increment(1);
                        node_name = "UNKNOWN_NODE";
                    }
                    */
                    path.addNode(node_name);
                    prev_node = node;
                }
            }
        }

        private long intPairToLong(int first, int second) {
            return (long) (first << 32) | (second & 0xFFFFFFFFL);
        }
    }

    public static class PathCountReducer extends MapReduceBase implements
            Reducer<IntPairWritable, Text, IntPairWritable, MyMapWritable> {

        @Override
        public void reduce(IntPairWritable node_pair, Iterator<Text> paths,
                OutputCollector<IntPairWritable, MyMapWritable> output,
                Reporter reporter) throws IOException {
            reporter.getCounter(COUNTERS.NODE_PAIR).increment(1);
            Map<String, Integer> counter = new HashMap<String, Integer>();
            while (paths.hasNext()) {
                String path = paths.next().toString();
                Integer count = counter.get(path);
                if (count == null) {
                    count = 0;
                }
                count += 1;
                counter.put(path, count);
            }
            MyMapWritable map = MyMapWritable.fromMap(counter);
            if (map == null) {
                reporter.getCounter(COUNTERS.NO_KEPT_PATHS).increment(1);
            }
            else {
                output.collect(node_pair, MyMapWritable.fromMap(counter));
            }
        }
    }

    public static class SourcePathMapper extends MapReduceBase implements
            Mapper<IntPairWritable, MyMapWritable, Text, IntPairWritable> {
        Text out_key = new Text();
        IntPairWritable out_value = new IntPairWritable();
        @Override
        public void map(IntPairWritable key, MyMapWritable value,
                OutputCollector<Text, IntPairWritable> output,
                Reporter reporter) throws IOException {
            int source = key.getFirst();
            int target = key.getSecond();
            for (Map.Entry<Writable, Writable> entry : value.entrySet()) {
                String path = ((Text) entry.getKey()).toString();
                int count = ((IntWritable) entry.getValue()).get();
                out_key.set(source + "\t" + path);
                out_value.set(target, count);
                output.collect(out_key, out_value);
            }
        }
    }

    public static class NormalizingReducer extends MapReduceBase implements
            Reducer<Text, IntPairWritable, Text, Text> {
        Text out_key = new Text();
        Text out_value = new Text();
        // TODO?: Maybe IntPairWritable should be converted to text earlier, so we only have to
        // have one place where we read files, but that would require changing a bunch of other
        // stuff, and it may be less efficient to pass around that ints.
        Map<Integer, String> node_names = new HashMap<Integer, String>();

        @Override
        public void configure(JobConf job) {
            Path[] local_files;
            try {
                local_files = DistributedCache.getLocalCacheFiles(job);
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
            try {
                String filename = local_files[0].toString();
                BufferedReader reader = new BufferedReader(new FileReader(filename));
                String line;
                while ((line = reader.readLine()) != null) {
                    String[] parts = line.split("\t");
                    node_names.put(Integer.parseInt(parts[0]), new String(parts[1]));
                }
                reader.close();
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }

        @Override
        public void reduce(Text key, Iterator<IntPairWritable> values,
                OutputCollector<Text, Text> output,
                Reporter reporter) throws IOException {
            int MIN_COUNT = 50;
            String source_path = key.toString();
            String[] parts = source_path.split("\t");
            int source_node = Integer.parseInt(parts[0]);
            String source_name = node_names.get(source_node);
            if (source_name == null) {
                reporter.getCounter(COUNTERS.NO_NODE_NAME_FOUND).increment(1);
                source_name = "UNKNOWN_NODE";
            } else {
                reporter.getCounter(COUNTERS.NODE_NAME_FOUND).increment(1);
            }
            String path = parts[1];
            ArrayList<Pair<Integer, Integer>> counts = new ArrayList<Pair<Integer, Integer>>();
            int sum = 0;
            int target_values = 0;
            while (values.hasNext()) {
                IntPairWritable value = values.next();
                int target = value.getFirst();
                int count = value.getSecond();
                sum += count;
                target_values++;
                counts.add(new Pair<Integer, Integer>(target, count));
            }
            if (sum < MIN_COUNT) {
                reporter.getCounter(COUNTERS.NOT_ENOUGH_WALKS).increment(1);
                return;
            }
            for (Pair<Integer, Integer> count : counts) {
                double prob = ((double) count.getRight()) / sum;
                String target_name = node_names.get(count.getLeft());
                if (target_name == null) {
                    reporter.getCounter(COUNTERS.NO_NODE_NAME_FOUND).increment(1);
                    target_name = "UNKNOWN_NODE";
                } else {
                    reporter.getCounter(COUNTERS.NODE_NAME_FOUND).increment(1);
                }
                out_key.set(source_name + " " + target_name);
                out_value.set(path + "\t" + prob + "\t" + sum + "\t" + target_values);
                output.collect(out_key, out_value);
            }
        }
    }

    static int printUsage() {
        System.out.println("Sorry, no usage information yet: TODO");
        ToolRunner.printGenericCommandUsage(System.out);
        return -1;
    }

    static COUNTERS getHopCounter(int size) {
        switch (size) {
            case 1: return COUNTERS.HOP_1;
            case 2: return COUNTERS.HOP_2;
            case 3: return COUNTERS.HOP_3;
            case 4: return COUNTERS.HOP_4;
            case 5: return COUNTERS.HOP_5;
            case 6: return COUNTERS.HOP_6;
            case 7: return COUNTERS.HOP_7;
            case 8: return COUNTERS.HOP_8;
            case 9: return COUNTERS.HOP_9;
            case 10: return COUNTERS.HOP_10;
            case 11: return COUNTERS.HOP_11;
            case 12: return COUNTERS.HOP_12;
            case 13: return COUNTERS.HOP_13;
            case 14: return COUNTERS.HOP_14;
            case 15: return COUNTERS.HOP_15;
        }
        return COUNTERS.MORE_THAN_15_HOPS;
    }

    public int run(String[] args) throws Exception {
        if (args.length != 2) {
            System.out.println("ERROR: Wrong number of parameters: " + args.length
                    + " instead of 2.");
            return printUsage();
        }
        String input_dir = args[0];
        String output_dir = args[1];
        String tmp_dir = "/tmp/mg1/walk_analyzer_intermediate/";
        String tmp_dir2 = "/tmp/mg1/walk_analyzer_intermediate2/";

        // Set up the first map reduce
        JobConf conf = new JobConf(getConf(), WalkAnalyzer.class);
        conf.setJobName("FirstWalkAnalyzerMapReduce");

        conf.setInputFormat(WalkFileInputFormat.class);
        conf.setMapperClass(WalkFileMapper.class);
        conf.setMapOutputKeyClass(IntWritable.class);
        conf.setMapOutputValueClass(IntPairWritable.class);

        conf.setReducerClass(WalkIdReducer.class);
        conf.setOutputKeyClass(IntWritable.class);
        conf.setOutputValueClass(IntPairArrayWritable.class);
        conf.setOutputFormat(SequenceFileOutputFormat.class);

        conf.set("mapred.child.java.opts", "-Xmx700M -Xss10M");
        conf.set("mapred.map.max.attempts", "50");
        conf.set("mapred.reduce.max.attempts", "50");
        conf.set("mapred.max.tracker.failures", "50");
        conf.set("mapred.reduce.tasks", "500");
        conf.set("mapred.job.map.memory.mb", "1500");
        conf.set("mapred.job.reduce.memory.mb", "1500");
        conf.set("mapred.compress.map.output", "true");

        FileInputFormat.setInputPaths(conf, new Path(input_dir));
        FileOutputFormat.setOutputPath(conf, new Path(tmp_dir));

        JobClient.runJob(conf);

        // Now the second map reduce
        conf = new JobConf(getConf(), WalkAnalyzer.class);
        conf.setJobName("SecondWalkAnalyzerMapReduce");

        conf.setInputFormat(SequenceFileInputFormat.class);
        conf.setMapperClass(NodePairMapper.class);
        conf.setMapOutputKeyClass(IntPairWritable.class);
        conf.setMapOutputValueClass(Text.class);

        conf.setReducerClass(PathCountReducer.class);
        conf.setOutputKeyClass(IntPairWritable.class);
        conf.setOutputValueClass(MyMapWritable.class);
        conf.setOutputFormat(SequenceFileOutputFormat.class);

        conf.set("mapred.child.java.opts", "-Xmx1300M -Xss10M");
        conf.set("mapred.map.max.attempts", "50");
        conf.set("mapred.reduce.max.attempts", "50");
        conf.set("mapred.max.tracker.failures", "50");
        conf.set("mapred.reduce.tasks", "500");
        conf.set("mapred.job.map.memory.mb", "2000");
        conf.set("mapred.job.reduce.memory.mb", "2040");
        conf.set("mapred.compress.map.output", "true");

        FileInputFormat.setInputPaths(conf, new Path(tmp_dir));
        FileOutputFormat.setOutputPath(conf, new Path(tmp_dir2));

        DistributedCache.addCacheFile(new Path("/user/amcnabb/walks_medium/node_names.tsv").toUri(), conf);
        DistributedCache.addCacheFile(new Path("/user/amcnabb/walks_medium/rel_names2.tsv").toUri(), conf);

        JobClient.runJob(conf);

        // And finally, the third map reduce
        conf = new JobConf(getConf(), WalkAnalyzer.class);
        conf.setJobName("ThirdWalkAnalyzerMapReduce");

        conf.setInputFormat(SequenceFileInputFormat.class);
        conf.setMapperClass(SourcePathMapper.class);
        conf.setMapOutputKeyClass(Text.class);
        conf.setMapOutputValueClass(IntPairWritable.class);

        conf.setReducerClass(NormalizingReducer.class);
        conf.setOutputKeyClass(IntPairWritable.class);
        conf.setOutputValueClass(Text.class);
        conf.setOutputFormat(TextOutputFormat.class);

        conf.set("mapred.child.java.opts", "-Xmx1300M -Xss10M");
        conf.set("mapred.map.max.attempts", "50");
        conf.set("mapred.reduce.max.attempts", "50");
        conf.set("mapred.max.tracker.failures", "50");
        conf.set("mapred.reduce.tasks", "500");
        conf.set("mapred.job.map.memory.mb", "2000");
        conf.set("mapred.job.reduce.memory.mb", "2040");
        conf.set("mapred.compress.map.output", "true");

        FileInputFormat.setInputPaths(conf, new Path(tmp_dir2));
        FileOutputFormat.setOutputPath(conf, new Path(output_dir));

        DistributedCache.addCacheFile(new Path("/user/amcnabb/walks_medium/node_names.tsv").toUri(), conf);

        JobClient.runJob(conf);

        return 0;
    }

    public static void main(String[] args) throws Exception {
        int res = ToolRunner.run(new Configuration(), new WalkAnalyzer(), args);
        System.exit(res);
    }

    public static class IntPairArrayWritable extends ArrayWritable {
        public IntPairArrayWritable() {
            super(IntPairWritable.class);
        }

        public IntPairArrayWritable(IntPairWritable[] values) {
            super(IntPairWritable.class, values);
        }

        public static IntPairArrayWritable fromArrayList(ArrayList<IntPairWritable> array) {
            IntPairArrayWritable writable = new IntPairArrayWritable();
            IntPairWritable[] values = new IntPairWritable[array.size()];
            for (int i=0; i<array.size(); i++) {
                values[i] = array.get(i);
            }
            writable.set(values);
            return writable;
        }

        public ArrayList<IntPairWritable> toArrayList() {
            ArrayList<IntPairWritable> array = new ArrayList<IntPairWritable>();
            for (Writable pair : this.get()) {
                IntPairWritable int_pair = (IntPairWritable) pair;
                array.add(int_pair);
            }
            return array;
        }
    }

    public static class MyMapWritable extends MapWritable {

        // TODO: make this configurable
        static int MIN_COUNT = 1;

        public static MyMapWritable fromMap(Map<String, Integer> counter) {
            MyMapWritable map = new MyMapWritable();
            int entries = 0;
            for (Map.Entry<String, Integer> entry : counter.entrySet()) {
                Text path = new Text(entry.getKey());
                IntWritable count = new IntWritable();
                count.set(entry.getValue());
                if (entry.getValue() > MIN_COUNT) {
                    map.put(path, count);
                    entries++;
                }
            }
            if (entries > 0) {
                return map;
            } else {
                return null;
            }
        }

        // Kind of inefficient, if you're going to iterate over everything again, but there are
        // some cases where this might be useful, as trying to look up keys by Text objects doesn't
        // work.
        public Map<String, Integer> toMap() {
            Map<String, Integer> map = new HashMap<String, Integer>();
            for (Map.Entry<Writable, Writable> entry : entrySet()) {
                String path = ((Text) entry.getKey()).toString();
                int count = ((IntWritable) entry.getValue()).get();
                map.put(path, count);
            }
            return map;
        }

        @Override
        public String toString() {
            StringBuilder builder = new StringBuilder();
            for (Map.Entry<Writable, Writable> entry : entrySet()) {
                Text path = (Text) entry.getKey();
                IntWritable count = (IntWritable) entry.getValue();
                builder.append(" " + path.toString());
                builder.append(": ");
                builder.append(count.get());
                builder.append(";");
            }
            return builder.toString();
        }
    }
}
