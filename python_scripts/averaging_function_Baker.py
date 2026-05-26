### CODE ###


# Import pandas and numpy, standard scientific data analysis libraries
import pandas as pd
import numpy as np



import_path = "/home/lidar/ingenium_cartographer/labtest5_pointcloud/labtest5.txt"  # file path of the pointcloud.txt file. User edits this manually. (Future optimization: make this file executable and pass this path a CLI parameter)
export_path = import_path[:len(import_path)-4] + "AVG" + import_path[len(import_path)-4:] # export path is the same as the import path, but with "AVG" before the file extension. So, if the import path is "labtest5.txt", the export path is "labtest5AVG.txt". This is done by slicing the string at the last 4 characters (the ".txt") and inserting "AVG" before that.



def import_dataframe(full_path):

    # Read the file at the path (an ASCII-format Stanford .ply) as a space-separated .csv. Specify that the file has no header row--it jumps straight into numbers
    csv = pd.read_csv(full_path, sep=' ', header=None)

    # Convert the datato in a Pandas dataframe object.
    df = pd.DataFrame(csv)  

    # Label the df columns. These can now be used in place of column indices.
    df.columns = ["x", "y", "z"] 

    print("DataFrame acquired.")
    return df



# average the df file in the axis omitted from the axes parameter. Axes should be a list containing some out of ["x", "y", "z"]. Step seems to be a float in meters, over which interval the axis omitted is averaged.
def get_avg(df, step, axes=[0,1,2]):  
    
    cols = ["x", "y", "z"] # List of all the columns in the df file.
    rounded_cols = ["rounded_x", "rounded_y", "rounded_z"] # Create a new list of headers. This used to be a complicated comprehension, but I didn't consider that additional computation to be time-saving or easier to read than just writing the list

    if (axes != [0,1,2]): # If the axes aren't at the default, assume the user passed a list of column names in string form.
        axes = [cols.index(n) for n in axes] # In this instance, urn the axes list back into column index numbers


    # For each column in cols:
    #    divide the values by step
    #    round the values to the nearest integer
    #    then multiply them again by step
    # For a given column in cols (eg. x), assign it to the rounded_col that's at the same place in the list.
    #    Because the first item in cols is "x" and the first item in rounded_cols is "rounded_x", the output of this operation on "x" is saved to "rounded_x"
    #    This also has the effect of adding 3 more columns to the df--we now have cols called:
    #           ["x", "y", "z", "rounded_x", "rounded_y", "rounded_z"]
    df[rounded_cols] = df[cols].div(step).round().mul(step) 
    
    # This one little line is really complicated!
    # First, select the following columns:
    #    Select the columns from *within* rounded_cols which are specified by the axes list.
    #       So, if the axes list is ["x", "z"], select ["rounded_x", "rounded_z"]
    #    That is this code phrase: [rounded_cols[n] for n in axes]
    # Next, "groupby" the rounded columns. That is:
    #     Look at the columns selected in the previous step. In this example, we selected ["rounded_x", "rounded_z"]
    #     Now, if within those two columns, there are multiple rows with the same values, put all those rows into the same "group"
    #     For our example, if at any point in the data, there's "row 42" with a given rounded_x and rounded_z, and "row 48" also has that same rounded_x and rounded_z, we're going to group "row 42" and "row 48", no matter what else is in "row 42" or "row 48"
    # Now that those rows have all been put in a group, go through each group:
    #     In each group, average all the xs, all the ys, all the zs, and all the rounded_xs, rounded_ys, and rounded_zs too. Average everything until what used to be a group is now only one row.
    #     The new row has one value for x, one value for y, one value for z, and one value for each of the rounded ones too
    # But actually, we don't care about the rounded ones anymore. We used them to split the dataframe into little boxes, but now that we've averaged all the point inside each box, we're done with them
    #     So now, out of all that dataframe, we only select [cols]--that is, we only select the x, y, and z columns
    #     That's what we return. 
    return df.groupby([rounded_cols[n] for n in axes]).mean()[cols]





# Average across all dimensions

# Flatten the z axis
df = import_dataframe(import_path)
averaged_df = get_avg(df, 0.03, ["x", "y"])
# So now, over here, we call averaging across columns "x" and "y". Here's what the algorithm does:
#    The algorithm divides the whole cloud into cubes with rounded_x, rounded_y, and rounded_z. The size of those cubes is determined by "step"--in this case, 0.3
#    Now, the algorithm looks at the params and sees we picked "x" and "y". So, all the points which have similar xs and similar ys (as determined by the rounding algorithm) all get grouped together
#    All the points in that little group of points with a similar x and a similar y get averaged accross all dimensions. One point is spit out--it has their average x, their average y, and their average z
#    Their average x and average y were already really close, because, if you remember, we picked points for this group which were close to each other in the x and y dimensions
#    But their zs were likely not very close at all, because we didn't select for that. So now, all the zs that were in that little column we selected have been replaced by their average z
#    To repurpose this for 3D voxel averaging, simply add a "z" parameter to the list there. 

print("Function Called.")
np.savetxt(export_path, averaged_df, delimiter=' ') # export the df in that space-delimited csv format again
print("Program has finished running.")




### NOTES ###

__NOTES__ = """
This file was copied off of averaging_function_Johannes.py by Abraham Baker 
Date Created: Jan 25 2025
Last Updated: May 26 2026
Purpose: Increase clarity and readability of the original without altering fundamental functionality

UPDATE LOG: WRITE BELOW HERE IF YOU ALTER THIS FILE

1. Abraham Baker, Jan 25 2025
    Created the file and added all the comments currently in it. 
    Also added the __NOTES__ string 
    modified get_avg to be more readable. For original see averaging_function_Johannes.py

2. Abraham Baker, May 26 2026
    Updated __NOTES__ string, clarified comments
    modified get_avg to be more readable. For original see averaging_function_Johannes.py
    moved some loose code into import_dataframe for organizational reasons
    Added export_path variable to make it easier to change the export path. It is now automatically generated from the import path, so the user only has to change the import path.
    Moved file to GitHub

3. [Your name], [date]
    [Brief summary of edits]
"""